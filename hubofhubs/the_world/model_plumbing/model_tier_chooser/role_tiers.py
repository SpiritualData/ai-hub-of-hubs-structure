"""The tier each model call role runs on: one table, ``role_tiers.csv`` beside this file, that the code reads.

A call names its ROLE (``tier_for("request_classification")``) and the table gives the tier; no call site names a tier of its own and no code names a
model. Tier names are the hub's four, the same as its main consumer's: ``fast``, ``balanced``, ``quality`` and ``best``. ``strong`` stays readable as an
alias of ``quality`` (here, in ``ALIASES``, and nowhere else), and the older chooser names ``cheap`` and ``mid`` read as ``fast`` and ``balanced``.
The chooser names a model for each of the four tiers from public evaluations (``cheap``, ``mid`` and ``strong`` are its older names for fast, balanced and quality; ``best`` is its own tier,
capability only): a call on ``best`` runs on the best tier's own default model, or fails with the reason when none is chosen, and never on another tier's model; ``resolution_note`` says so. A person's explicit tier wins for a role whose ``person_may_set`` is ``yes``; a role
whose tier is the name of another role follows it. ``best`` is reached only by a person's explicit tier or by the role ``structure-watch`` (``BEST_ROLE``), which another part of the hub builds. The ``evidence`` cell is computed (see ``compute_table``): the public evaluations, the two tiers' scores, the gap against the threshold, the date, direct or
proxy; no row rests on a preference. Reading the table is standard library only; computing it imports ``public_metric`` and ``tiers`` inside the functions.
The table path is an argument, nothing is read from the environment."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Mapping, Optional

TABLE = Path(__file__).with_name("role_tiers.csv")
TIERS = ("fast", "balanced", "quality", "best")
ALIASES = {"strong": "quality", "cheap": "fast", "mid": "balanced", "science": "fast"}     # science is a call role, not a tier: it reads as fast
CHOOSER_TIER = {"fast": "cheap", "balanced": "mid", "quality": "strong", "best": "best"}
BEST_ROLE = "structure-watch"


def normalise(tier: str) -> str:
    """The hub's name for a tier, aliases resolved (``strong`` is ``quality``); an unknown name is returned as given, lower case."""
    name = (tier or "").strip().lower()
    return ALIASES.get(name, name)


def chooser_tier(tier: str) -> str:
    """The tier the model tier chooser measures for ``tier``."""
    return CHOOSER_TIER.get(normalise(tier), normalise(tier))


def resolution_note(tier: str) -> str:
    """What to say when the tier does not have an arm measured for itself, else an empty string."""
    if normalise(tier) == "best":
        return "the best tier runs on its own default model, chosen from public evaluations for capability alone; with no model chosen for it the call fails with the reason and does not run on another tier"
    return ""


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The role-tier metric. The tier of a role is computed, not chosen: ``role_tier_metrics.csv`` (written before any role was computed) says, for each
# kind of call, which public evaluations speak to it (direct or proxy), the ladder, the frequency and stakes classes and the base gain; the role's
# own row of ``role_tiers.csv`` gives its kind, frequency class and stakes class. The role takes the lowest tier of the ladder unless the next tier up
# shows a gain on the kind's evaluations that reaches
#     threshold = base_gain x frequency factor x price premium / stakes factor
# where the price premium is log2 of the next tier's list price over this tier's (never below 1). Hard constraints (classification fast only, a
# response a person reads at least balanced, best only for the structure watch) are applied after the metric and recorded as such; the row still
# shows what the metric alone picked. The models that fill the tiers come from the tier choice (``tiers.choose``), never from a name here.
# ``compute_table`` recomputes the whole table from the registry for a day; ``write_table`` writes it. The generated columns are ``tier``,
# ``metric_tier``, ``constraint``, ``computed_on`` and ``evidence``; the others are inputs. No clock is read: the day is an argument.
# ---------------------------------------------------------------------------------------------------------------------------------------------
METRIC_RULES = Path(__file__).with_name("role_tier_metrics.csv")
INPUT_COLUMNS = ("role", "kind", "frequency", "stakes", "follows", "person_may_set", "own_measurement", "reason")
COLUMNS = ("role", "kind", "frequency", "stakes", "follows", "person_may_set", "tier", "metric_tier", "constraint", "computed_on", "evidence",
           "own_measurement", "reason")


def read_rules(path: Path = METRIC_RULES) -> list:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _scoped(rules: list, part: str, kind: str, role: str) -> list:
    """The rows of a part for a role, else for its kind, else for ``all``: a narrower scope replaces a wider one whole."""
    for scope in (lambda r: r["role"] == role and role, lambda r: r["kind"] == kind and not r["role"], lambda r: r["kind"] == "all" and not r["role"]):
        found = [r for r in rules if r["part"] == part and scope(r)]
        if found:
            return found
    return []


def rule_value(rules: list, part: str, key: str) -> float:
    for r in rules:
        if r["part"] == part and r["key"] == key:
            return float(r["value"])
    raise KeyError(f"role_tier_metrics.csv has no {part} row {key!r}")


def ladder_for(rules: list, kind: str = "", role: str = "") -> tuple:
    """The tiers the metric climbs for a kind or role, lowest first, up to the ``top_of_metric`` tier."""
    rows = sorted(_scoped(rules, "ladder", kind, role), key=lambda r: float(r["value"]))
    top = next(r["value"] for r in rules if r["part"] == "rule" and r["key"] == "top_of_metric")
    tiers = [r["key"] for r in rows]
    return tuple(tiers[: tiers.index(top) + 1]) if top in tiers else tuple(tiers)


def evaluations_for(rules: list, kind: str, role: str = "") -> Dict[str, tuple]:
    """``{measure: (weight, fit)}`` of the evaluations that speak to a kind (or to a role that has its own)."""
    return {r["key"]: (float(r["weight"]), r["fit"]) for r in _scoped(rules, "evaluation", kind, role)}


def threshold(rules: list, frequency: str, stakes: str, price_low: float, price_high: float) -> tuple:
    """``(threshold, premium)``: base gain x frequency factor x price premium / stakes factor."""
    import math
    premium = max(1.0, math.log2(price_high / price_low)) if price_low > 0 and price_high > 0 else 1.0
    return rule_value(rules, "rule", "base_gain") * rule_value(rules, "frequency", frequency) * premium / rule_value(rules, "stakes", stakes), premium


def gain(evals: Mapping[str, tuple], low: Mapping, high: Mapping) -> dict:
    """The gain of ``high`` over ``low`` on the evaluations, in shares of the better of the two (0 to 1; an Elo rating reads as the chance of beating the
    better one). An evaluation either has no number on is dropped and listed, never guessed, and its weight is shared among the others."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric as pm
    used = {m: wf for m, wf in evals.items() if low.get(m) is not None and high.get(m) is not None}
    dropped = sorted(set(evals) - set(used))
    total = sum(w for w, _ in used.values())
    if not used or total <= 0:
        return dict(gain=None, used={}, dropped=dropped, direct=0.0)
    value = sum((w / total) * (pm.normalise(m, high[m], max(low[m], high[m])) - pm.normalise(m, low[m], max(low[m], high[m]))) for m, (w, _) in used.items())
    direct = sum(w for w, f in used.values() if f == "direct") / total
    return dict(gain=value, used={m: (low[m], high[m]) for m in used}, dropped=dropped, direct=direct)


def climb(rules: list, kind: str, role: str, frequency: str, stakes: str, arms: Mapping[str, Mapping], prices: Mapping[str, float], day: str,
          max_age: float = 45) -> dict:
    """Walk the ladder: stay on a tier unless the next tier up shows a gain that reaches the threshold. ``arms`` is ``{tier: public row}`` and ``prices``
    ``{tier: list price}``. Returns ``{tier, steps, unmeasured, direct, newest, oldest}``; ``tier`` is None, with ``unmeasured`` saying why, when a number
    the walk needs is stale, missing or unpriced (a stale number is reported, never used)."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric as pm
    rungs = ladder_for(rules, kind, role)
    evals = evaluations_for(rules, kind, role)
    current, steps, direct = rungs[0], [], []
    for low, high in zip(rungs, rungs[1:]):
        if current != low:
            break
        problems = []
        for tier in (low, high):
            row = arms.get(tier)
            age = pm.age_days(row, day) if row else None
            if row is None:
                problems.append(f"no model for the {tier} tier")
            elif age is None or age > max_age:
                problems.append(f"the {tier} tier's numbers are {'undated' if age is None else str(age) + ' days old'} (limit {max_age:g})")
            if not prices.get(tier):
                problems.append(f"no list price for the {tier} tier")
        if problems:
            return dict(tier=None, steps=steps, unmeasured="; ".join(problems), direct=0.0, newest="", oldest="")
        got = gain(evals, arms[low], arms[high])
        if got["gain"] is None:
            return dict(tier=None, steps=steps, unmeasured=f"no evaluation of the kind {kind} has a number on both the {low} and the {high} tier", direct=0.0, newest="", oldest="")
        limit, premium = threshold(rules, frequency, stakes, prices[low], prices[high])
        up = got["gain"] >= limit and got["gain"] > 0
        steps.append(dict(low=low, high=high, gain=got["gain"], limit=limit, premium=premium, up=up, used=got["used"], dropped=got["dropped"]))
        direct.append(got["direct"])
        if up:
            current = high
    dates = sorted(arms[t]["checked_on"] for t in rungs if arms.get(t))
    return dict(tier=current, steps=steps, unmeasured="", direct=min(direct) if direct else 0.0, newest=dates[-1] if dates else "", oldest=dates[0] if dates else "")


def constraints_for(rules: list, kind: str, role: str) -> list:
    """The hard constraints that apply to a role (by role, or by kind when the row names no role): ``[(name, action, reason)]``."""
    return [(r["key"], r["value"], r["reason"]) for r in rules if r["part"] == "constraint" and ((r["role"] and r["role"] == role) or (not r["role"] and r["kind"] == kind))]


def apply_constraints(tier: str, constraints: list, order: tuple = TIERS) -> str:
    for _, action, _ in constraints:
        how, _, target = action.partition(":")
        if how == "fixed":
            tier = target
        elif how == "min" and order.index(tier) < order.index(target):
            tier = target
    return tier


def describe_step(step: dict) -> str:
    scores = ", ".join(f"{m} {a:g} to {b:g}" for m, (a, b) in step["used"].items())
    drop = f"; no number on both for {', '.join(step['dropped'])}" if step["dropped"] else ""
    verdict = "step up" if step["up"] else "stay"
    return (f"{step['low']} to {step['high']}: gain {step['gain']:+.3f} against threshold {step['limit']:.3f}, {verdict} "
            f"(scores of the {step['low']} tier's model to the {step['high']} tier's: {scores}{drop})")


def role_row(inputs: Mapping[str, str], rules: list, arms: Mapping[str, Mapping], prices: Mapping[str, float], day: str, previous: Optional[Mapping[str, str]] = None,
             max_age: float = 45) -> Dict[str, str]:
    """One finished row: the inputs plus the generated ``tier``, ``metric_tier``, ``constraint``, ``computed_on`` and ``evidence``."""
    role, kind = inputs["role"], inputs["kind"]
    got = climb(rules, kind, role, inputs["frequency"], inputs["stakes"], arms, prices, day, max_age)
    rungs = ladder_for(rules, kind, role)
    held = (previous or {}).get(role, "")
    metric_tier = got["tier"] or (held if held in TIERS else rungs[0])
    cons = constraints_for(rules, kind, role)
    final = apply_constraints(metric_tier, cons)
    if got["tier"]:
        kindword = "direct" if got["direct"] >= 0.5 else "proxy"
        head = (f"{kindword} public evidence (direct weight {got['direct']:.2f}); numbers dated {got['oldest']} to {got['newest']}, none older than {max_age:g} days on {day}; "
                f"frequency {inputs['frequency']}, stakes {inputs['stakes']}; ")
        body = "; ".join(describe_step(s) for s in got["steps"]) + f". The metric alone picks {metric_tier}."
    else:
        head = f"STALE OR MISSING public numbers on {day}, the metric was not applied: {got['unmeasured']}. "
        body = f"The previous tier {metric_tier} is kept until the registry is refreshed."
    if cons:
        names = ", ".join(n for n, _, _ in cons)
        tail = (f" The constraint {names} set the tier to {final} (the metric alone would have picked {metric_tier})." if final != metric_tier
                else f" The constraint {names} holds and agrees with the metric.")
    else:
        tail = ""
    follow = f" The role follows {inputs['follows']}, so its tier is that role's." if inputs.get("follows") else ""
    row = {c: inputs.get(c, "") for c in COLUMNS}
    row.update(tier=inputs["follows"] or final, metric_tier=metric_tier, constraint="; ".join(n for n, _, _ in cons), computed_on=day, evidence=head + body + tail + follow)
    return row


def tier_fillers(day: str, folder=None) -> tuple:
    """``({tier: public row}, {tier: list price})`` of the model each tier names on ``day`` (the tier choice), from the registry; a tier with no public
    row or price is left out and the walk reports it."""
    from hubofhubs.the_world.learning.research_freshness_reader import registry
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric as pm, tiers
    choice = tiers.choose(folder=folder, today=day)
    public = pm.candidates(folder)
    prices = registry.read("tier_prices.csv", folder)
    arms, cost = {}, {}
    for tier in TIERS:
        got = choice.get(tier)
        if not got or not got.get("arm"):
            continue
        provider, model = got["arm"]
        row = next((r for r in public if (r["provider"], r["model"]) == (provider, model) and (r["effort"] == got.get("effort") if got.get("effort") else r.get("is_default") == "yes")), None)
        rate = tiers.rates(prices, provider, model, day=day)
        if row is not None:
            arms[tier] = row
        if rate:
            cost[tier] = sum(rate)
    return arms, cost


def read_inputs(path: Path = TABLE) -> list:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return [{c: row.get(c, "") for c in INPUT_COLUMNS} | {"tier": row.get("tier", "")} for row in csv.DictReader(handle)]


def compute_table(day: str, folder=None, inputs: Optional[list] = None, rules: Optional[list] = None, path: Path = TABLE) -> list:
    """The whole table recomputed from the registry for ``day`` (an ISO date): one dict per role, in the order of the inputs. Stale numbers are reported in
    the row and the previous tier (the ``tier`` or ``metric_tier`` already on file) is kept."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import public_metric as pm
    inputs = read_inputs(path) if inputs is None else inputs
    rules = read_rules() if rules is None else rules
    arms, prices = tier_fillers(day, folder)
    max_age = pm.setting(pm.read_metrics(), "freshness", "scores", 45)
    previous = {}
    if Path(path).exists():
        with Path(path).open(newline="", encoding="utf-8") as handle:
            previous = {r["role"]: (r.get("metric_tier") or r.get("tier") or "") for r in csv.DictReader(handle)}
    return [role_row(i, rules, arms, prices, day, previous, max_age) for i in inputs]


def write_table(day: str, folder=None, path: Path = TABLE) -> list:
    rows = compute_table(day, folder, path=path)
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def read_table(path: Path = TABLE) -> Dict[str, Dict[str, str]]:
    """``{role: row}`` of the table."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return {row["role"]: row for row in csv.DictReader(handle)}


def tier_for(role: str, requested: str = "", table: Optional[Mapping[str, Mapping[str, str]]] = None) -> str:
    """The tier of ``role``. ``requested`` (a person's explicit tier) wins when the role lets a person set it; a role that names another role follows it.
    Raises ``KeyError`` for a role the table does not hold, so a typo fails where it is written."""
    rows = table if table is not None else read_table()
    seen = []
    while True:
        if role not in rows:
            raise KeyError(f"no tier policy for the role {role!r}; roles: {', '.join(sorted(rows))}")
        if role in seen:
            raise ValueError(f"the tier policy of {role!r} follows itself")
        seen.append(role)
        row = rows[role]
        if requested and (row.get("person_may_set") or "").strip().lower() == "yes":
            return normalise(requested)
        tier = normalise(row.get("tier") or "")
        if tier in TIERS:
            return tier
        role = tier
