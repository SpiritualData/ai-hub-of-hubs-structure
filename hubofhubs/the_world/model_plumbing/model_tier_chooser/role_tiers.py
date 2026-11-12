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
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional

StandingTierGuidance = Callable[[str], str]
"""The port for a person's earlier guidance on model tiers: given a role, the tier the person has asked that role to run on, or an empty string. The hub holds no
store of a person's preferences; the consumer supplies this function from its own (a Representative's preferences, a settings file, a memory)."""

STANDINGS = Path(__file__).resolve().parents[2] / "tools" / "delegated_agent_sessions" / "arm_standings.json"
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
# The deep-run roles (the ``deep_run`` rows of the rule file) do not use that climb. Their definition is the owner's: the default is the cheapest tier whose
# recorded pass rate on the deep-work cases meets the sufficiency bar (``sufficient_tier``); a person's tier, from the current request first and then from
# standing guidance (``StandingTierGuidance``, a function the consumer supplies), wins over it (``choose_tier``); when the default fails a task the planner
# moves that task up one rung with a recorded reason (``escalate``), never for later tasks; a sub-agent runs on its own default unless the main session
# asks for more with a reason (``sub_agent_choice``). Nothing is stored between tasks, so no choice is sticky. A deep-run role may have its own evidence
# source (the ``own_evidence`` rows: file editing reads its own component of the results file, ``own_pass_rates``) in place of the deep-work cases, under the same
# bar; a run counts only within the expiry and when recorded under the model the tier names that day, and a tier with no counting run is unmeasured. A role that
# cannot be lowered by any evidence carries a stated constraint instead (connected system operations: ``min:quality``, a person may still set higher).
# ``compute_table`` recomputes the whole table from the registry for a day; ``write_table`` writes it. The generated columns are ``tier``,
# ``metric_tier``, ``constraint``, ``computed_on`` and ``evidence``; the others are inputs. No clock is read: the day is an argument.
# ---------------------------------------------------------------------------------------------------------------------------------------------
METRIC_RULES = Path(__file__).with_name("role_tier_metrics.csv")
INPUT_COLUMNS = ("role", "kind", "frequency", "stakes", "volume", "tokens_in", "tokens_out", "volume_basis", "task_kind", "follows", "person_may_set", "own_measurement", "reason")
COLUMNS = ("role", "kind", "frequency", "stakes", "volume", "tokens_in", "tokens_out", "volume_basis", "task_kind", "follows", "person_may_set", "tier", "metric_tier",
           "constraint", "computed_on", "evidence", "own_measurement", "reason")


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


def volume_of(rules: list, volume: str, tokens_in: str = "", tokens_out: str = "") -> tuple:
    """``(input, output, cache write, cache read)`` tokens per call: the measured numbers the role row gives (volume ``measured``; no cache tokens) or the
    class's (the ``volume`` row gives input in weight and output in value, in thousands; ``volume_cache_write`` and ``volume_cache_read`` rows give the cache
    tokens in value)."""
    if volume == "measured":
        return float(tokens_in), float(tokens_out), 0.0, 0.0
    row = next((r for r in rules if r["part"] == "volume" and r["key"] == volume), None)
    if row is None:
        raise KeyError(f"role_tier_metrics.csv has no volume class {volume!r}")
    cache = {part: next((float(r["value"]) * 1000 for r in rules if r["part"] == part and r["key"] == volume), 0.0) for part in ("volume_cache_write", "volume_cache_read")}
    return float(row["weight"]) * 1000, float(row["value"]) * 1000, cache["volume_cache_write"], cache["volume_cache_read"]


def call_cost(price: tuple, tokens: tuple) -> float:
    """The list cost in USD of one call. ``price`` is ``(input, output[, cache read multiplier, cache write multiplier])`` in USD per million tokens (a missing
    multiplier counts as 1: no discount is assumed); ``tokens`` is ``(input, output[, cache write, cache read])``. Cache writes and reads are priced as
    their multipliers of the input price."""
    read_m, write_m = (price[2], price[3]) if len(price) > 3 else (1.0, 1.0)
    write_t, read_t = (tokens[2], tokens[3]) if len(tokens) > 3 else (0.0, 0.0)
    return (price[0] * tokens[0] + price[1] * tokens[1] + price[0] * write_m * write_t + price[0] * read_m * read_t) / 1e6


def required_gain(rules: list, frequency: str, stakes: str, price_low: tuple, price_high: tuple, tokens: tuple) -> dict:
    """What a step up must show: the larger of the noise floor and ``cost_weight x added cost / value of gain``. The added cost is the expected cost of
    the role's calls: calls per turn or run x (cost of a call on the higher tier's model minus on the lower's), each ``call_cost`` of the list prices with
    cache reads and writes at their multipliers of the input price. Returns ``{limit, added_cost, value, calls, by_cost}``."""
    calls = rule_value(rules, "frequency", frequency)
    added = calls * (call_cost(price_high, tokens) - call_cost(price_low, tokens))
    value = rule_value(rules, "stakes", stakes)
    by_cost = rule_value(rules, "rule", "cost_weight") * max(added, 0.0) / value
    return dict(limit=max(rule_value(rules, "rule", "noise_floor"), by_cost), added_cost=added, value=value, calls=calls, by_cost=by_cost)


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


def climb(rules: list, kind: str, role: str, frequency: str, stakes: str, arms: Mapping[str, Mapping], prices: Mapping[str, tuple], day: str,
          max_age: float = 45, tokens: tuple = (840.0, 76.0)) -> dict:
    """Walk the ladder: stay on a tier unless the next tier up shows a gain that reaches ``required_gain`` (the larger of the noise floor and the cost
    weight times the expected added cost over the value of gain). ``arms`` is ``{tier: public row}``, ``prices`` ``{tier: (input, output) list price}``
    and ``tokens`` the (input, output) tokens per call of the role. Returns ``{tier, steps, unmeasured, direct, newest, oldest}``; ``tier`` is None, with ``unmeasured`` saying why, when a number
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
        need = required_gain(rules, frequency, stakes, prices[low], prices[high], tokens)
        up = got["gain"] >= need["limit"] and got["gain"] > 0
        steps.append(dict(low=low, high=high, gain=got["gain"], limit=need["limit"], need=need, up=up, used=got["used"], dropped=got["dropped"]))
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


def deep_run_roles(rules: list) -> tuple:
    """The roles the deep-run definition applies to: the ``deep_run`` rows of the rule file."""
    return tuple(r["role"] for r in rules if r["part"] == "deep_run" and r["role"])


def measured_pass_rates(path: Path = STANDINGS, kind: str = "hard") -> Dict[str, dict]:
    """``{tier: {passed, total, arms, first, last}}`` of the recorded deep-work cases: for each arm row of the kind in the standings file, the passed and total
    cases of its latest pooled row, summed per tier (the ``tier=`` of the arm's name). A tier with no row is absent, never guessed; an unreadable file gives ``{}``."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    found: Dict[str, dict] = {}
    for arm, runs in (((data.get("kinds") or {}).get(kind) or {}).get("rows") or {}).items():
        named = re.search(r"tier=([A-Za-z]+)", arm)
        if not named or not isinstance(runs, dict) or not runs:
            continue
        row = runs[max(runs, key=lambda k: int(k) if str(k).isdigit() else 0)]
        try:
            passed, total = int(row["passed_total"]), int(row["cases_total"])
        except (KeyError, TypeError, ValueError):
            continue
        tier = normalise(named.group(1))
        slot = found.setdefault(tier, dict(passed=0, total=0, arms=0, first=str(row.get("date", "")), last=str(row.get("date", ""))))
        slot["passed"] += passed
        slot["total"] += total
        slot["arms"] += 1
        slot["first"], slot["last"] = min(slot["first"], str(row.get("date", ""))), max(slot["last"], str(row.get("date", "")))
    return found


RESULTS = Path(__file__).resolve().parents[4] / "esoi" / "results.csv"


def own_evidence_for(rules: list, role: str) -> dict:
    """The role's own evidence source, from the ``own_evidence`` rows of the rule file: ``{component, arms: {tier: impl}}``, or ``{}`` for a role that is judged on
    the deep-work cases. Such a role is measured by its own component of the results file, not by the deep-work cases; the same bar applies."""
    rows = [r for r in rules if r["part"] == "own_evidence" and r["role"] == role]
    component = next((r["value"] for r in rows if r["key"] == "component"), "")
    arms = {r["key"].partition(":")[2]: r["value"] for r in rows if r["key"].startswith("arm:")}
    return dict(component=component, arms=arms) if component else {}


def own_pass_rates(rules: list, role: str, day: str, current_models: Optional[Mapping[str, str]] = None, path: Path = RESULTS) -> tuple:
    """``(measured, caveats)`` of a role judged on its own component: for each tier's arm, the passed and total cases of its latest full row (no sample) in the results
    file, in the shape of ``measured_pass_rates``. A row counts only when it is no older than ``evidence_max_age_days`` on ``day`` and was recorded under the model the
    tier names on ``day`` (``current_models``, ``{tier: model}``); a row that fails either is left out and ``caveats`` says which, so a measurement of another model is
    never read as the tier's. A tier with no counting row is absent, never guessed; an unreadable file gives ``({}, [...])``."""
    own = own_evidence_for(rules, role)
    if not own:
        return {}, []
    import datetime
    limit = rule_value(rules, "sufficiency", "evidence_max_age_days")
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            rows = [r for r in csv.DictReader(handle) if r.get("component") == own["component"] and not (r.get("sample") or "").strip()]
    except OSError:
        return {}, [f"the results file could not be read, so the component {own['component']} has no recorded measurement"]
    measured, caveats = {}, []
    for tier, impl in own["arms"].items():
        mine = [r for r in rows if r.get("impl") == impl]
        if not mine:
            caveats.append(f"no full recorded run of the {tier} arm {impl}")
            continue
        row = max(enumerate(mine), key=lambda pair: (pair[1].get("date", ""), pair[0]))[1]
        age = (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(row["date"])).days
        if age > limit:
            caveats.append(f"the latest run of the {tier} arm {impl} is dated {row['date']}, {age} days old on {day}, past the {limit:g} day expiry, so it is not used")
        elif (current_models or {}).get(tier) != row.get("model"):
            caveats.append(f"the latest run of the {tier} arm {impl} ({row['passed']} of {row['cases']} cases, {row['date']}) was recorded under a different model from the one "
                           f"the {tier} tier names on {day}, so it is not a measurement of the {tier} tier and is not used")
        else:
            measured[tier] = dict(passed=int(row["passed"]), total=int(row["cases"]), arms=1, first=row["date"], last=row["date"])
    return measured, caveats


def sufficient_tier(rules: list, measured: Mapping[str, Mapping], rungs: Optional[tuple] = None, what: str = "the recorded deep-work cases") -> dict:
    """The default tier of a deep-run role: the lowest rung whose measured pass rate meets the sufficiency bar. A rung with no measurement is skipped (the
    cheapest MEASURED rung that meets the bar is the answer, and ``note`` says which rungs were skipped). When no measured rung meets the bar the tier is the rung
    above the highest measured one; when nothing is measured the tier is None. ``what`` names the cases the rate is over. Returns ``{tier, bar, note}``."""
    bar = rule_value(rules, "sufficiency", "pass_rate_bar")
    rungs = rungs or ladder_for(rules)
    parts, skipped, tier = [], [], None
    for rung in rungs:
        got = measured.get(rung)
        if not got or not got["total"]:
            skipped.append(rung)
            continue
        rate = got["passed"] / got["total"]
        parts.append(f"{rung} {got['passed']} of {got['total']} ({rate:.3f}) over {got['arms']} arm rows, {got['first']} to {got['last']}")
        if tier is None and rate >= bar:
            tier = rung
    if tier is None and parts:
        top = max(i for i, rung in enumerate(rungs) if rung in measured and measured[rung]["total"])
        tier = rungs[min(top + 1, len(rungs) - 1)]
        parts.append("no measured tier meets the bar, so the rung above the highest measured one")
    skip = f"; no measurement for {', '.join(skipped)}, so the rule falls to the cheapest measured tier that meets the bar" if skipped and tier else ""
    return dict(tier=tier, bar=bar, note=(f"measured pass rate on {what}: {'; '.join(parts)}{skip}" if parts else f"no tier has a measurement on {what}"))


@dataclass(frozen=True)
class TierChoice:
    """A tier chosen for a role, with where it came from and why. ``source`` is ``current_input``, ``standing_guidance``, ``default``, ``main_session_ask`` or
    ``escalation``; ``reason`` is the recorded note (specific for an escalation or an ask); ``from_tier`` is the tier an escalation left."""
    role: str
    tier: str
    source: str
    reason: str = ""
    from_tier: str = ""

    def record(self) -> Dict[str, str]:
        """The keys to merge into the run's own record or event: ``tier``, ``tier_source``, ``tier_reason`` (and ``tier_from`` for an escalation)."""
        out = {"tier": self.tier, "tier_source": self.source, "tier_reason": self.reason}
        if self.from_tier:
            out["tier_from"] = self.from_tier
        return out


def known_tier(tier: str) -> str:
    name = normalise(tier)
    if name not in TIERS:
        raise ValueError(f"{tier!r} is not a tier; the tiers are {', '.join(TIERS)}")
    return name


def settable_role(role: str, rows: Mapping[str, Mapping[str, str]]) -> str:
    """The role in the follow chain of ``role`` whose ``person_may_set`` is yes, or an empty string when a person may not set it."""
    seen = []
    while role in rows and role not in seen:
        seen.append(role)
        row = rows[role]
        if (row.get("person_may_set") or "").strip().lower() == "yes":
            return role
        follows = (row.get("follows") or "").strip() or (row.get("tier") or "").strip()
        role = follows if follows not in TIERS else ""
    return ""


def choose_tier(role: str, requested: str = "", standing: Optional[StandingTierGuidance] = None, table: Optional[Mapping[str, Mapping[str, str]]] = None,
                rules: Optional[list] = None) -> TierChoice:
    """The tier of ``role`` for one task, in this order: the tier the person names in the current request (``requested``), the tier their standing guidance on model
    tiers names (``standing(role)``), else the table's default (for a deep-run role, the cheapest sufficient tier). The first two apply only to a role a person may
    set. Nothing is remembered between calls. Raises ``KeyError`` for an unknown role and ``ValueError`` for a name that is not a tier."""
    rows = table if table is not None else read_table()
    if role not in rows:
        raise KeyError(f"no tier policy for the role {role!r}; roles: {', '.join(sorted(rows))}")
    if settable_role(role, rows):
        if (requested or "").strip():
            return TierChoice(role, known_tier(requested), "current_input", "the person named this tier in the current request")
        held = (standing(role) if standing else "") or ""
        if held.strip():
            return TierChoice(role, known_tier(held), "standing_guidance", "the person's standing guidance on model tiers names this tier")
    rules = read_rules() if rules is None else rules
    followed = rows[role].get("follows") or ""
    deep = role in deep_run_roles(rules) or followed in deep_run_roles(rules)
    why = ("the cheapest tier whose recorded pass rate on the deep-work cases meets the sufficiency bar" if deep else "the role table's tier for the role")
    return TierChoice(role, tier_for(role, "", rows), "default", why)


def escalate(choice: TierChoice, signal: str, reason: str, rules: Optional[list] = None) -> TierChoice:
    """The choice for the one task whose default tier fell short: one rung up the ladder, with the recorded reason. ``signal`` is what said the result was
    insufficient (the ``escalation`` signal rows of the rule file: after_check, stop_decision or review); ``reason`` must say specifically what the tier did not do.
    A blank reason, one that only repeats the signal, a role that is not a deep-run role, a tier that is not on the ladder (best) and the top rung are refused.
    Nothing is stored: the caller uses the returned choice for this task only and chooses again for the next."""
    rules = read_rules() if rules is None else rules
    signals = [r["value"] for r in rules if r["part"] == "escalation" and r["key"] == "signal"]
    if signal not in signals:
        raise ValueError(f"the signal {signal!r} is not one of {', '.join(signals)}")
    text = " ".join((reason or "").split())
    if not text or text.lower() in (signal, signal.replace("_", " ")):
        raise ValueError("an escalation needs a specific reason: what the tier did not do sufficiently on this task")
    if choice.role not in deep_run_roles(rules):
        raise ValueError(f"{choice.role!r} is not a deep-run role, so it is not escalated")
    rungs = ladder_for(rules)
    if choice.tier not in rungs:
        raise ValueError(f"{choice.tier!r} is not a rung the planner climbs; best is a person's explicit tier or the structure watch")
    at = rungs.index(choice.tier)
    if at + 1 >= len(rungs):
        raise ValueError(f"{choice.tier!r} is the top rung; there is no higher tier to escalate to")
    return TierChoice(choice.role, rungs[at + 1], "escalation", f"{signal}: {text}", from_tier=choice.tier)


SUB_AGENT_ROLE = "sub_agent"


def sub_agent_choice(asked: str = "", reason: str = "", table: Optional[Mapping[str, Mapping[str, str]]] = None, rules: Optional[list] = None) -> TierChoice:
    """The tier of a sub-agent: its own default (the cheapest sufficient tier), whatever the main session runs on, unless the main session asks for a named tier
    and gives a reason, which is recorded. A request with no reason is refused."""
    if (asked or "").strip():
        text = " ".join((reason or "").split())
        if not text:
            raise ValueError("the main session must give a reason when it asks a sub-agent to run on a higher tier")
        return TierChoice(SUB_AGENT_ROLE, known_tier(asked), "main_session_ask", text)
    return choose_tier(SUB_AGENT_ROLE, table=table, rules=rules)


def describe_step(step: dict) -> str:
    scores = ", ".join(f"{m} {a:g} to {b:g}" for m, (a, b) in step["used"].items())
    drop = f"; no number on both for {', '.join(step['dropped'])}" if step["dropped"] else ""
    verdict = "step up" if step["up"] else "stay"
    need = step["need"]
    bound = "cost" if need["by_cost"] > need["limit"] - 1e-12 and need["by_cost"] > 0 else "noise floor"
    return (f"{step['low']} to {step['high']}: gain {step['gain']:+.3f} against threshold {step['limit']:.3f} ({bound} binds; added cost {need['added_cost']:.4f} USD per turn or run "
            f"at {need['calls']:g} calls, value of a full gain {need['value']:g} USD), {verdict} "
            f"(scores of the {step['low']} tier's model to the {step['high']} tier's: {scores}{drop})")


def deep_run_row(inputs: Mapping[str, str], rules: list, measured: Mapping[str, Mapping], day: str, previous: Optional[Mapping[str, str]] = None,
                 own: Optional[tuple] = None) -> Dict[str, str]:
    """One finished row of a deep-run role: the tier is the cheapest sufficient one (``sufficient_tier``), the evidence is the recorded pass rates against the bar.
    ``own`` is ``(measured, caveats)`` of a role judged on its own component (``own_pass_rates``): its rates replace the deep-work cases and the caveats are stated."""
    role, kind = inputs["role"], inputs["kind"]
    component = own_evidence_for(rules, role).get("component", "") if own is not None else ""
    if component:
        measured, caveats = own
        what, label = f"the recorded cases of the component {component}", f"numbers of the role's own measurement, the component {component}"
    else:
        caveats, what, label = [], "the recorded deep-work cases", "numbers of the recorded hard deep-work cases"
    got = sufficient_tier(rules, measured, what=what)
    rungs = ladder_for(rules, kind, role)
    held = (previous or {}).get(role, "")
    metric_tier = got["tier"] or (held if held in TIERS else rungs[0])
    cons = constraints_for(rules, kind, role)
    final = apply_constraints(metric_tier, cons)
    said = (" Caveats: " + "; ".join(caveats) + ".") if caveats else ""
    if got["tier"]:
        head = f"sufficiency rule (cheapest tier good enough for most deep work, bar {got['bar']:g} pass rate, {label}); {got['note']}. The rule picks {metric_tier}.{said}"
    else:
        head = (f"STALE OR MISSING measurement on {day}, the rule was not applied: {got['note']}.{said} "
                f"The previous tier {metric_tier} is kept until a current measurement of the tier is recorded.")
    tail = f" The constraint {', '.join(n for n, _, _ in cons)} set the tier to {final}." if cons and final != metric_tier else ""
    follow = f" The role follows {inputs['follows']}, so its tier is that role's." if inputs.get("follows") else ""
    row = {c: inputs.get(c, "") for c in COLUMNS}
    row.update(tier=inputs["follows"] or final, metric_tier=metric_tier, constraint="; ".join(n for n, _, _ in cons), computed_on=day, evidence=head + tail + follow)
    return row


def role_row(inputs: Mapping[str, str], rules: list, arms: Mapping[str, Mapping], prices: Mapping[str, tuple], day: str, previous: Optional[Mapping[str, str]] = None,
             max_age: float = 45, measured: Optional[Mapping[str, Mapping]] = None, own: Optional[tuple] = None) -> Dict[str, str]:
    """One finished row: the inputs plus the generated ``tier``, ``metric_tier``, ``constraint``, ``computed_on`` and ``evidence``. A deep-run role takes the
    sufficiency rule over ``measured`` (``measured_pass_rates``), or over its own component's ``own`` (``own_pass_rates``) when the rule file gives it one; every
    other role takes the climb. A role with its own evidence and no ``own`` given is read against the models the ``arms`` name."""
    role, kind = inputs["role"], inputs["kind"]
    if role in deep_run_roles(rules):
        if own is None and own_evidence_for(rules, role):
            own = own_pass_rates(rules, role, day, {tier: row["model"] for tier, row in arms.items() if row.get("model")})
        return deep_run_row(inputs, rules, measured if measured is not None else measured_pass_rates(), day, previous, own)
    tokens = volume_of(rules, inputs.get("volume", "small") or "small", inputs.get("tokens_in", ""), inputs.get("tokens_out", ""))
    klass = next((r for r in rules if r["part"] == "volume" and r["key"] == (inputs.get("volume") or "small")), {})
    basis = (f"measured: {inputs['volume_basis']}" if inputs.get("volume") == "measured"
             else f"measured class {inputs.get('volume')}: median of recorded Claude Code sessions" if klass.get("fit") == "measured" else f"estimated class {inputs.get('volume') or 'small'}")
    got = climb(rules, kind, role, inputs["frequency"], inputs["stakes"], arms, prices, day, max_age, tokens)
    rungs = ladder_for(rules, kind, role)
    held = (previous or {}).get(role, "")
    metric_tier = got["tier"] or (held if held in TIERS else rungs[0])
    cons = constraints_for(rules, kind, role)
    final = apply_constraints(metric_tier, cons)
    if got["tier"]:
        kindword = "direct" if got["direct"] >= 0.5 else "proxy"
        head = (f"{kindword} public evidence (direct weight {got['direct']:.2f}); numbers dated {got['oldest']} to {got['newest']}, none older than {max_age:g} days on {day}; "
                f"frequency {inputs['frequency']}, stakes {inputs['stakes']}, tokens per call {tokens[0]:g} in, {tokens[1]:g} out, {tokens[2]:g} cache write, {tokens[3]:g} cache read ({basis}); ")
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
    """``({tier: public row}, {tier: (input, output) list price})`` of the model each tier names on ``day`` (the tier choice), from the registry; a tier
    with no public row or price is left out and the walk reports it."""
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
            row_price = next((r for r in prices if (r["provider"], r["model"]) == (provider, model) and tiers.in_force(r, day) and not (r.get("from_prompt_tokens") or "").strip()), {})
            mult = lambda name: float(row_price.get(name) or 1.0)         # a blank multiplier means no cache discount is assumed
            cost[tier] = (rate[0], rate[1], mult("cache_read_multiplier"), mult("cache_write_multiplier"))
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
    measured = measured_pass_rates()
    return [role_row(i, rules, arms, prices, day, previous, max_age, measured) for i in inputs]


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


MAIN_ROLE = "main_session"


def task_kinds(table: Optional[Mapping[str, Mapping[str, str]]] = None) -> Dict[str, str]:
    """``{task kind: deep-work role}`` from the table's ``task_kind`` column (for example gather, implementation, structure, review)."""
    rows = table if table is not None else read_table()
    return {row["task_kind"]: role for role, row in rows.items() if (row.get("task_kind") or "").strip()}


def deep_work_role(task_kind: str = "", table: Optional[Mapping[str, Mapping[str, str]]] = None) -> str:
    """The role a deep-work session runs as: the role of its task kind, or ``main_session`` (which follows the implementation role) when the kind is
    not given or is not one the table knows. The task kind comes from a classification the caller already made on the fast tier, never from words."""
    return task_kinds(table).get((task_kind or "").strip().lower(), MAIN_ROLE)


def task_choice(task_kind: str = "", requested: str = "", table: Optional[Mapping[str, Mapping[str, str]]] = None,
                standing: Optional[StandingTierGuidance] = None) -> TierChoice:
    """The tier choice of a deep-work session of ``task_kind``: the current request's tier, else the standing guidance's, else the cheapest sufficient tier."""
    rows = table if table is not None else read_table()
    return choose_tier(deep_work_role(task_kind, rows), requested, standing, rows)


def tier_for_task(task_kind: str = "", requested: str = "", table: Optional[Mapping[str, Mapping[str, str]]] = None,
                  standing: Optional[StandingTierGuidance] = None) -> str:
    """The tier of a deep-work session of ``task_kind`` (see ``task_choice``); a person's tier wins, as for any role that lets a person set it."""
    return task_choice(task_kind, requested, table, standing).tier
