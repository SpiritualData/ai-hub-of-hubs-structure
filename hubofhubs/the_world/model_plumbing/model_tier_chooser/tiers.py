"""Tier selection by metric: per model tier, pick the (provider, model) arm with the most passing work per unit of cost.

Pure functions over data: no model call, no network. An arm is a dict with ``provider``, ``model``, ``cases`` (shared cases run),
``passed`` and the token totals ``tokens_in`` and ``tokens_out`` those cases used. Prices come from ``tier_prices.csv`` (per
million tokens, with a source URL and a checked-on date). Prepaid credits are the consumer's own: it
passes its rows (``provider``, ``balance``, ``allowance``, ``credit_value``) to ``choose`` or ``pick``; the hub ships ``tier_credits.csv`` as the
schema only and holds no organization's allowance.

Cost of an arm = money actually spent after credits + ``credit_value`` x the credits it used. Credits are therefore never free:
``credit_value`` (0 to 1) is what a credit is worth to the owner if it were not used here (1 when unused credit is not lost,
lower when it expires). A credit row whose ``credit_value`` is blank is counted at its face value (1): the value is not defaulted
in the data, and the reading that never understates cost applies until it is confirmed.
"""
from datetime import date

from esoi import implementation

from hubofhubs.the_world.learning.research_freshness_reader import registry
from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric
from hubofhubs.the_self.assembler import arm_needs as needs

MIN_CASES = 1


def in_force(row, day):
    """Whether a price row applies on ``day`` (an ISO date): ``valid_from`` and ``valid_until`` are inclusive and blank when open."""
    return (not row.get("valid_from") or row["valid_from"] <= day) and (not row.get("valid_until") or day <= row["valid_until"])


def rates(prices, provider, model, prompt_tokens=0, day=None):
    """``(input, output)`` USD per million tokens for a model, or None when no row in force holds a number. A model may have
    several rows: ``from_prompt_tokens`` marks a higher rate for prompts at least that long (the longest threshold reached wins),
    and ``valid_from`` / ``valid_until`` a price change on a date. The hub reads no clock for the rule: pass ``day`` to fix it."""
    day = day or date.today().isoformat()
    rows = [r for r in prices if r["provider"] == provider and r["model"] == model and in_force(r, day)
            and int(number(r.get("from_prompt_tokens"))) <= prompt_tokens]
    if not rows:
        return None
    row = max(rows, key=lambda r: number(r.get("from_prompt_tokens")))
    try:
        return float(row["input_per_mtok"]), float(row["output_per_mtok"])
    except (TypeError, ValueError):
        return None


def list_cost(prices, provider, model, tokens_in, tokens_out, prompt_tokens=None, day=None):
    """The list price in USD of ``tokens_in`` and ``tokens_out`` on a model, or None when it is not priced. ``prompt_tokens`` (the
    length of the prompt, default ``tokens_in``) picks the rate tier."""
    got = rates(prices, provider, model, tokens_in if prompt_tokens is None else prompt_tokens, day)
    return None if got is None else tokens_in / 1e6 * got[0] + tokens_out / 1e6 * got[1]


def price_of(prices, arm):
    """The base ``(input, output)`` price for an arm (a prompt under any threshold), or None when there is none."""
    return rates(prices, arm["provider"], arm["model"])


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def credit_value(text):
    """What a credit is worth (0 to 1); blank or unreadable is face value (1), so an unconfirmed value never understates cost."""
    try:
        return min(1.0, max(0.0, float(text)))
    except (TypeError, ValueError):
        return 1.0


def credit_of(credits, provider):
    """(available amount, credit_value) for a provider: balance plus allowance, 0 when no row or no number."""
    for row in credits:
        if row["provider"] == provider:
            return number(row.get("balance")) + number(row.get("allowance")), credit_value(row.get("credit_value"))
    return 0.0, 1.0


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


def measured_arms(folder=None):
    """``{tier: [arm]}`` from ``tier_measurements.csv`` (one row per tier and arm: cases, passed, tokens_in, tokens_out)."""
    out = {}
    for r in registry.read("tier_measurements.csv", folder):
        out.setdefault(LEGACY_TIERS.get(r["tier"], r["tier"]), []).append(dict(provider=r["provider"], model=r["model"], cases=int(number(r["cases"])),
                                                   passed=int(number(r["passed"])), tokens_in=int(number(r["tokens_in"])),
                                                   tokens_out=int(number(r["tokens_out"]))))
    return out


LEGACY_TIERS = {"cheap": "fast", "mid": "balanced", "strong": "quality"}     # the chooser's older tier names, still read by a consumer that has not moved


def providers_available(environ):
    """The providers whose model caller can run on this install, from the mapping given (no environment is read): a key in the mapping, or for
    Anthropic a logged-in Claude CLI binary on its PATH. Needs are the callers' own ``REQUIRES`` (``arm_needs``), checked as availability checks them."""
    from esoi.runtime.assemble_by_name.seat_blockers import unmet_checks
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.anthropic import AnthropicProvider
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.gemini import GeminiProvider
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.openai import DeepSeekProvider, OpenAIProvider
    callers = (("anthropic", AnthropicProvider), ("anthropic", ClaudeCliProvider), ("gemini", GeminiProvider), ("openai", OpenAIProvider),
               ("deepseek", DeepSeekProvider))
    return sorted({name for name, cls in callers if not unmet_checks(cls, environ, {})})


def choose(folder=None, available=None, credits=None, today="", role="", environ=None, effort_providers=(), **bars):
    """``{tier: {arm, effort, reason, scored, stage, evidence}}`` for the four tiers (fast, balanced, quality, best), and the older names (cheap, mid,
    strong) as the same entries. The model a tier defaults to is decided by public evaluations, list price and published speed only
    (``public_metric``: tier_metrics.csv over tier_public_scores.csv and tier_prices.csv): the cheapest and fastest arm that is at least as good as the
    tier's held default (``tier_arms.csv``) on every evaluation the tier names, less a tolerance, with capability above that earning a small bonus; ``scored`` is the ranking and ``reason`` names the runner-up. ``evidence`` is ``proxy``
    when the evaluations only stand in for the tier's use. The hub's own measurements do not decide the model of a tier: the role-tier metric
    (``role_tiers.compute_table``, over the same public rows) decides which tier a call role uses. With no arm clearing the minimums the held default of ``tier_arms.csv`` stays (stage
    ``held``), else the cheapest priced available arm. ``available`` (providers a consumer has configured; None for all) restricts the arms, or
    ``environ`` (a mapping the caller gives) derives it with ``providers_available``. ``effort_providers`` names the providers whose caller applies the
    returned effort (none today: only each model's documented default effort competes). ``role`` names a domain of call (for example ``science``)
    whose metric variant, if the tier has one, replaces the tier's minimums and capability weights. ``today`` is an ISO date (default: today).
    ``credits`` and ``bars`` are accepted for callers of ``select`` and ``pick`` and are not used here."""
    held, candidates = default_arms(folder)
    prices = registry.read("tier_prices.csv", folder)
    day = today or date.today().isoformat()
    if available is None and environ is not None:
        available = providers_available(environ)
    ok = lambda pair: available is None or pair[0] in available
    rows = public_metric.read_metrics()
    rate = lambda provider, model: rates(prices, provider, model, day=day)      # the list price in force today
    out = {}
    for tier in sorted(set(held) | set(candidates) | set(public_metric.TIERS)):
        public = public_metric.choose_public(tier, folder, available, day, role, rows, effort_providers=effort_providers, rate=rate,
                                             anchor=held.get(tier))
        if public:
            out[tier] = dict(public, scored=public["ranking"])
            continue
        # no arm clears the tier on current public numbers: the held default of tier_arms.csv stays, else the cheapest priced available arm
        held_pair = held.get(tier) if tier in held and ok(held[tier]) else None
        pairs = [p for p in ([held[tier]] if tier in held else []) + candidates.get(tier, []) if ok(p) and rates(prices, *p)]
        if held_pair:
            out[tier] = dict(arm=held_pair, effort="", stage="held", scored=[], reason="no arm clears the tier's minimums on current public numbers: kept the held default")
        elif pairs:
            out[tier] = dict(arm=min(pairs, key=lambda p: sum(rates(prices, *p))), effort="", stage="held", scored=[],
                             reason="no current public numbers and the held arm is not available: the cheapest priced available arm")
        else:
            out[tier] = dict(arm=None, effort="", stage="held", scored=[], reason="no priced available arm: none chosen")
    for old, new in LEGACY_TIERS.items():
        if new in out:
            out[old] = out[new]
    return out


def served_models(provider, folder=None, today=""):
    """The models of ``provider`` the hub can serve, in the order of the tier ladder (the chosen arm of each tier first, then the held defaults and the
    candidates of ``tier_arms.csv`` that have a price in force), without repeats. Read from the chooser and its registry, never written here; a consumer's
    model picker lists these after the tiers, and a person may name one for a session (``explicit_model``)."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.role_tiers import TIERS
    wanted = (provider or "").strip().lower()
    chosen = choose(folder, available={wanted}, today=today)
    held, candidates = default_arms(folder)
    prices = registry.read("tier_prices.csv", folder)
    day = today or date.today().isoformat()
    pairs = [chosen[t]["arm"] for t in TIERS if (chosen.get(t) or {}).get("arm")]
    for t in TIERS:
        pairs += ([held[t]] if t in held else []) + candidates.get(t, [])
    seen = {}
    for pair_provider, model in pairs:
        if pair_provider == wanted and (rates(prices, pair_provider, model, day=day) is not None or any(c["arm"] == (pair_provider, model) for c in chosen.values() if c.get("arm"))):
            seen[model] = None
    return list(seen)


def explicit_model(provider, name, folder=None):
    """The model id ``name`` names among ``served_models(provider)`` (case does not matter), or None when the hub does not serve a model by that name. A tier name is never a model."""
    wanted = (name or "").strip().lower()
    return next((m for m in served_models(provider, folder) if m.lower() == wanted), None) if wanted else None


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


@implementation("model-tier-chooser", "tier_selector")
class TierSelector:
    """The tier selector as one registered implementation of the model-tier-chooser solution: the functions above, behind an
    object a consumer can build and hand around. Pure functions, no state."""
    REQUIRES = ()     # pure functions
    price_of = staticmethod(price_of)
    arm_cost = staticmethod(arm_cost)
    evaluate_arm = staticmethod(evaluate_arm)
    pick = staticmethod(pick)
    select = staticmethod(select)
    default_arms = staticmethod(default_arms)
    choose = staticmethod(choose)
    list_cost = staticmethod(list_cost)
    portfolio = staticmethod(portfolio)
    scripted_choices = staticmethod(scripted_choices)
