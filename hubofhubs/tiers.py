"""Tier selection by metric: per model tier, pick the (provider, model) arm with the most passing work per unit of cost.

Pure functions over data: no model call, no network. An arm is a dict with ``provider``, ``model``, ``cases`` (shared cases run),
``passed`` and the token totals ``tokens_in`` and ``tokens_out`` those cases used. Prices come from ``tier_prices.csv`` (per
million tokens, with a source URL and a checked-on date). Prepaid credits come from ``tier_credits.csv``.

Cost of an arm = money actually spent after credits + ``credit_value`` x the credits it used. Credits are therefore never free:
``credit_value`` (0 to 1) is what a credit is worth to the owner if it were not used here (1 when unused credit is not lost,
lower when it expires).
"""
from esoi import implementation

from . import registry

MIN_CASES = 1


def price_of(prices, arm):
    """The price row for an arm, or None when there is none or it holds no number."""
    for row in prices:
        if row["provider"] == arm["provider"] and row["model"] == arm["model"]:
            try:
                return float(row["input_per_mtok"]), float(row["output_per_mtok"])
            except (TypeError, ValueError):
                return None
    return None


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def credit_of(credits, provider):
    """(available amount, credit_value) for a provider: balance plus allowance, 0 when no row or no number."""
    for row in credits:
        if row["provider"] == provider:
            return number(row.get("balance")) + number(row.get("allowance")), min(1.0, max(0.0, number(row.get("credit_value"))))
    return 0.0, 0.0


def arm_cost(arm, prices, credits):
    """(list cost, money spent after credits, credits used, effective cost), or None when the arm cannot be priced."""
    price = price_of(prices, arm)
    if price is None:
        return None
    listed = arm["tokens_in"] / 1e6 * price[0] + arm["tokens_out"] / 1e6 * price[1]
    available, value = credit_of(credits, arm["provider"])
    used = min(listed, available)
    spent = listed - used
    return listed, spent, used, spent + value * used


def evaluate_arm(arm, prices, credits, min_cases=MIN_CASES):
    """The arm with its measured pass rate, costs and passing work per cost; ``eligible`` is false without a measurement."""
    cost = arm_cost(arm, prices, credits)
    measured = arm["cases"] >= min_cases
    out = dict(provider=arm["provider"], model=arm["model"], cases=arm["cases"], passed=arm["passed"],
               pass_rate=(arm["passed"] / arm["cases"]) if arm["cases"] else 0.0, eligible=measured and cost is not None)
    if cost is not None:
        out.update(list_cost=cost[0], money_spent=cost[1], credits_used=cost[2], cost=cost[3])
        out["passing_per_cost"] = float("inf") if cost[3] <= 0 and arm["passed"] else (arm["passed"] / cost[3] if cost[3] > 0 else 0.0)
    return out


def pick(arms, prices, credits=(), default=None, min_cases=MIN_CASES, min_pass_rate=0.0):
    """Choose one tier's arm: ``{arm, reason, scored}``. ``default`` is the (provider, model) held now.

    Floor: nothing switches without a measurement. The held arm stays unless it and the winner are both measured and priced.
    Winner: highest passing work per cost, the cheaper arm on a tie, among arms at or above ``min_pass_rate``."""
    scored = [evaluate_arm(a, prices, credits, min_cases) for a in arms]
    held = next((s for s in scored if default and (s["provider"], s["model"]) == tuple(default)), None)
    pool = [s for s in scored if s["eligible"] and s["pass_rate"] >= min_pass_rate]
    if not pool:
        return dict(arm=tuple(default) if default else None, scored=scored,
                    reason="no measured and priced arm at the pass-rate bar: kept the default" if default else "no measured arm: none chosen")
    best = min(pool, key=lambda s: (-s["passing_per_cost"], s["cost"]))
    if default and (held is None or not held["eligible"]):
        return dict(arm=tuple(default), scored=scored, reason="the held arm has no measurement or price to compare against: kept it")
    arm = (best["provider"], best["model"])
    why = (f"{best['passing_per_cost']:.3g} passing cases per cost at pass rate {best['pass_rate']:.2f}, cost {best['cost']:.4g}"
           f" (money {best['money_spent']:.4g}, credits used {best['credits_used']:.4g})")
    if default and arm == tuple(default):
        why = "kept: best passing work per cost, " + why
    return dict(arm=arm, scored=scored, reason=why)


def select(tiers, prices, credits=(), defaults=None, **bars):
    """Pick per tier. ``tiers`` is ``{tier: [arm, ...]}``; ``defaults`` is ``{tier: (provider, model)}``."""
    return {tier: pick(arms, prices, credits, (defaults or {}).get(tier), **bars) for tier, arms in tiers.items()}


def default_arms(folder=None):
    """``{tier: (provider, model)}`` held by default, and ``{tier: [candidate (provider, model)]}`` still to be measured."""
    held, candidates = {}, {}
    for row in registry.read("tier_arms.csv", folder):
        pair = (row["provider"], row["model"])
        if row["role"] == "default":
            held[row["tier"]] = pair
        else:
            candidates.setdefault(row["tier"], []).append(pair)
    return held, candidates


def portfolio(choices, tiers, prices, credits=()):
    """Passing cases per unit of cost over all tiers for a ``{tier: (provider, model)}`` choice (an unpriced choice counts as 0)."""
    passed = cost = 0.0
    for tier, pair in choices.items():
        arm = next((a for a in tiers[tier] if (a["provider"], a["model"]) == tuple(pair)), None)
        got = arm_cost(arm, prices, credits) if arm else None
        if got is None:
            continue
        passed += arm["passed"]
        cost += got[3]
    return passed / cost if cost > 0 else 0.0


def scripted_choices(tiers, prices, credits=(), **bars):
    """The scripted ideal: what ``select`` picks."""
    return {t: r["arm"] for t, r in select(tiers, prices, credits, **bars).items()}


def by_price(tiers, prices, pick_one):
    out = {}
    for tier, arms in tiers.items():
        best = pick_one(arms, key=lambda a: sum(price_of(prices, a) or (0.0, 0.0)))
        out[tier] = (best["provider"], best["model"])
    return out


def always_most_expensive(tiers, prices):
    """Broken baseline one: the highest-priced model in every tier."""
    return by_price(tiers, prices, max)


def always_cheapest(tiers, prices):
    """Broken baseline two: the lowest-priced model in every tier, whatever its quality."""
    return by_price(tiers, prices, min)


@implementation("reason-and-answer", "tier_selector")
class TierSelector:
    """The tier selector as one registered implementation of the reason-and-answer seat: the functions above, behind an
    object a consumer can build and hand around. Pure functions, no state."""
    price_of = staticmethod(price_of)
    arm_cost = staticmethod(arm_cost)
    evaluate_arm = staticmethod(evaluate_arm)
    pick = staticmethod(pick)
    select = staticmethod(select)
    default_arms = staticmethod(default_arms)
    portfolio = staticmethod(portfolio)
    scripted_choices = staticmethod(scripted_choices)
