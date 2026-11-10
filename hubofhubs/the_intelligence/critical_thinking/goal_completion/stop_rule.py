"""stop_rule: the stop decision of Goal Completion as plain code, no model call.

Role: iteration the person did not ask for (the hub resuming a session after its own check, a text loop nudging again, a worker of the solution
hierarchy re-worked) has no natural end, so something has to say when to stop. The rule here reads an iteration history and answers with one
of ``continue``, ``stop_met``, ``stop_good_enough`` (and what is left), ``stop_not_worth_it`` (a plateau, an oscillation, a regress, or a cost that
exceeds the expected gain) and ``ask`` (what is missing only a person can supply, or a ceiling the person could raise).

ESOI side: iterate only while the expected gain toward the next milestone is worth the cost of the next step. The evidence that a costlier step is
justified is the cheaper evidence already in hand: the share of the remaining gap the last iteration closed (``MIN_GAIN_SHARE``), and that share
against the share of the remaining budget it cost (the cascading-conditional idea). A plateau, an oscillation or a regress stops; a milestone that
is already reached stops, because the furthest useful future is past it.

Consciousness side: what the person stated (one pass only, keep going until X, stop) outranks the default; policy and the Representative's authority
bound it (they are plain inputs, resolved from Consciousness solutions by the caller, see
``hubofhubs.the_consciousness.representatives.stop_limits``); anything only a person can supply means ``ask`` and never another iteration; the
ceilings are never overridden, only raised by the person (so under "keep going" a reached ceiling is an ``ask``).

The history, all of it optional:

    {"iterations": [{"verdict": True | False | None,     # Goal Completion's check of that iteration's outcome (None: not checked)
                     "claimed_met": bool | None,          # what the worker said about itself: never trusted
                     "outcome": {"text": ..., "coverage": ...} | None,
                     "changed": int,                      # what the iteration changed (files, rows, units)
                     "metric": float | None,              # the metric value after it, where there is one
                     "missing": [str],                    # what the check found missing
                     "spend_usd": float, "seconds": float}],   # that iteration's own cost
     "metric": {"better": "higher" | "lower", "target": float, "good_enough": float} | None,
     "ceiling": {"spend_usd": float | None, "seconds": float | None, "soft_fraction": 0.8},
     "milestone": {"text": str, "reached": bool},
     "stated": {"stop": bool, "one_pass": bool, "max_iterations": int, "keep_going_until": str, "until_reached": bool},
     "policy": {"forbids_iteration": bool, "max_iterations": int, "authority_exhausted": bool},
     "needs_human": str | bool}

Standard library only."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

CONTINUE, STOP_MET, STOP_GOOD_ENOUGH, STOP_NOT_WORTH_IT, ASK = "continue", "stop_met", "stop_good_enough", "stop_not_worth_it", "ask"
DECISIONS = (CONTINUE, STOP_MET, STOP_GOOD_ENOUGH, STOP_NOT_WORTH_IT, ASK)
STOP_DECISIONS = DECISIONS     # the name the front door exports

MIN_GAIN_SHARE = 0.05       # an iteration that closes less than this share of the remaining gap is a plateau
FIRST_COST_SHARE = 0.5      # before any gain is known, a first iteration that cost half the remaining budget does not earn a second
DEFAULT_ITERATION_CAP = 5   # the hub's own iteration is bounded whatever else is said; the person's "keep going" lifts it
SOFT_FRACTION = 0.8         # the share of a ceiling after which no new iteration starts (the same figure as the runners' soft limit)
FIXED_CAP = 2               # the iterations the fixed-cap baseline allows


def number(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def iterations_of(history: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return [dict(x) for x in (history.get("iterations") or []) if isinstance(x, Mapping)]


def verdict_of(iteration: Mapping[str, Any]) -> bool:
    """Whether the iteration was met by the check. A worker's own claim and an unchecked iteration are not met."""
    return iteration.get("verdict") is True


def totals(history: Mapping[str, Any]) -> Dict[str, float]:
    its = iterations_of(history)
    return {"spend_usd": sum(number(i.get("spend_usd")) or 0.0 for i in its), "seconds": sum(number(i.get("seconds")) or 0.0 for i in its)}


def budget_shares(history: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    """The share of each ceiling used so far (None for a dimension with no ceiling)."""
    used, ceiling = totals(history), history.get("ceiling") or {}
    out: Dict[str, Optional[float]] = {}
    for key, name in (("spend_usd", "spend"), ("seconds", "time")):
        cap = number(ceiling.get(key))
        out[name] = used[key] / cap if cap and cap > 0 else None
    return out


def measure(history: Mapping[str, Any]) -> Dict[str, Any]:
    """The progress series: metric values (the metric where each iteration has one, else the count of what the check found missing, lower is better,
    target zero), the direction and the target."""
    its, spec = iterations_of(history), history.get("metric") or {}
    values = [number(i.get("metric")) for i in its]
    if its and all(v is not None for v in values):
        better, target = str(spec.get("better") or "higher"), number(spec.get("target"))
        return {"values": values, "better": better, "target": target, "kind": "metric"}
    counts = [len(i.get("missing") or []) if isinstance(i.get("missing"), (list, tuple)) else None for i in its]
    if its and all(c is not None for c in counts) and any(counts):
        return {"values": [float(c) for c in counts], "better": "lower", "target": 0.0, "kind": "missing"}
    return {"values": [], "better": "higher", "target": None, "kind": "none"}


def gains(series: Mapping[str, Any]) -> List[float]:
    """The improvement each iteration made over the one before (positive is better), as a signed amount."""
    values, sign = series["values"], 1.0 if series["better"] == "higher" else -1.0
    return [sign * (b - a) for a, b in zip(values, values[1:])]


def gap_before(series: Mapping[str, Any], index: int) -> Optional[float]:
    """The remaining gap to the target before the value at ``index`` (a positive amount), None when there is no target."""
    target, values = series["target"], series["values"]
    if target is None or index < 0 or index >= len(values):
        return None
    return max(abs(target - values[index]), 1e-9)


def oscillates(series: Mapping[str, Any]) -> bool:
    """Up, down, up (or down, up, down) in the last three gains and the last value no better than the best before it: the series is going round."""
    g = gains(series)
    if len(g) < 3 or not all(g[-3:][i] * g[-3:][i + 1] < 0 for i in range(2)):
        return False
    values, sign = series["values"], 1.0 if series["better"] == "higher" else -1.0
    best_before = max(sign * v for v in values[:-1])
    gap = gap_before(series, 0)
    scale = gap if gap is not None else max(abs(x) for x in g[-3:])
    return (sign * values[-1] - best_before) / scale < MIN_GAIN_SHARE


def result(decision: str, code: str, reason: str, facts: Mapping[str, Any], left: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"decision": decision, "continue": decision == CONTINUE, "code": code, "reason": reason, "facts": dict(facts)}
    if left:
        out["left"] = left
    return out


def what_is_left(history: Mapping[str, Any]) -> str:
    its = iterations_of(history)
    missing = list(its[-1].get("missing") or []) if its else []
    human = history.get("needs_human")
    parts = [str(x) for x in missing] + ([str(human)] if isinstance(human, str) and human else [])
    return "; ".join(parts) or "what the done-standard still asks for"


def decide(history: Mapping[str, Any], met: Optional[bool] = None) -> Dict[str, Any]:
    """The stop decision for ``history``. ``met`` replaces the last iteration's verdict when the caller (the independent reviewer) re-derived it.
    Order: a person's stated wish and the bounds first, then the evidence of progress against cost."""
    its = iterations_of(history)
    n = len(its)
    stated, policy, milestone = history.get("stated") or {}, history.get("policy") or {}, history.get("milestone") or {}
    shares, soft = budget_shares(history), number((history.get("ceiling") or {}).get("soft_fraction")) or SOFT_FRACTION
    used = totals(history)
    facts: Dict[str, Any] = {"iterations": n, "spend_usd": round(used["spend_usd"], 4), "seconds": round(used["seconds"], 1),
                             "spend_share": shares["spend"], "time_share": shares["time"]}
    last_met = (verdict_of(its[-1]) if its else False) if met is None else bool(met)
    until = bool(stated.get("keep_going_until"))
    until_done = bool(stated.get("until_reached"))
    facts["met"] = last_met
    left = what_is_left(history)
    if until and last_met and not until_done:
        last_met = False          # the person's own stop condition outranks the done-standard
    if last_met and (not until or until_done):
        return result(STOP_MET, "met", "the goal is met against its done-standard", facts)
    if until and until_done:
        return result(STOP_MET, "until_reached", "what the person asked to keep going until is reached", facts)
    if milestone.get("reached"):
        return result(STOP_MET, "milestone_reached", "the next milestone is already reached: more iteration aims past it", facts)
    if stated.get("stop"):
        return result(STOP_GOOD_ENOUGH, "person_stopped", "the person asked to stop", facts, left)
    limit = stated.get("max_iterations") if isinstance(stated.get("max_iterations"), int) else (1 if stated.get("one_pass") else None)
    if limit is not None and n >= limit:
        return result(STOP_GOOD_ENOUGH, "person_limit", f"the person asked for {limit} pass{'' if limit == 1 else 'es'} and it is done", facts, left)
    if policy.get("forbids_iteration"):
        return result(STOP_GOOD_ENOUGH, "policy", "policy does not allow the hub to iterate on this unasked", facts, left)
    policy_cap = policy.get("max_iterations")
    if isinstance(policy_cap, int) and n >= policy_cap:
        return result(STOP_GOOD_ENOUGH, "policy_cap", f"policy allows {policy_cap} iterations and they are used", facts, left)
    if policy.get("authority_exhausted"):
        return result(ASK, "authority", "the Representative's authority for this is used up; the person can extend it", facts, left)
    if history.get("needs_human") and not last_met:
        return result(ASK, "needs_human", "what is missing only a person can supply, so another iteration cannot supply it", facts, left)
    reached = max((s for s in shares.values() if s is not None), default=0.0)
    if reached >= 1.0 or reached >= soft:
        if until:
            return result(ASK, "ceiling_with_keep_going", "the person asked to keep going and the ceiling is reached: raising it is theirs to say", facts, left)
        which = "time" if (shares["time"] or 0.0) > (shares["spend"] or 0.0) else "spend"
        return result(STOP_GOOD_ENOUGH, f"ceiling_{which}", "the ceiling is reached: a natural, safe stopping point", facts, left)
    if n == 0:
        return result(CONTINUE, "first", "nothing has been tried yet", facts)
    if until:
        return result(CONTINUE, "keep_going", "the person asked to keep going and what they asked for is not reached", facts)
    series = measure(history)
    spec = history.get("metric") or {}
    value, target, good = (series["values"][-1] if series["values"] else None), series["target"], number(spec.get("good_enough"))
    if value is not None and good is not None and (value >= good if series["better"] == "higher" else value <= good):
        return result(STOP_GOOD_ENOUGH, "good_enough", "the metric is at the level the person accepts; what is left is small", facts, left)
    if n >= DEFAULT_ITERATION_CAP:
        return result(STOP_GOOD_ENOUGH, "iteration_cap", f"{n} unasked iterations are the bound; what is left is reported", facts, left)
    last = its[-1]
    if not (number(last.get("changed")) or 0) and series["kind"] != "metric":
        return result(STOP_NOT_WORTH_IT, "plateau", "the last iteration changed nothing", facts, left)
    cost = max(shares[k] for k in shares if shares[k] is not None) if any(v is not None for v in shares.values()) else 0.0
    gain_list = gains(series)
    if gain_list:
        g = gain_list[-1]
        if g < 0:
            return result(STOP_NOT_WORTH_IT, "regress", "the last iteration made it worse: keep the best one and stop", dict(facts, gain=g), left)
        if oscillates(series):
            return result(STOP_NOT_WORTH_IT, "oscillation", "the value goes up and down with no net gain: another iteration repeats the cycle", facts, left)
        gap = gap_before(series, len(series["values"]) - 2)
        share = g / gap if gap is not None else (1.0 if g > 0 else 0.0)
        last_cost = number(last.get("spend_usd")) or 0.0
        cap = number((history.get("ceiling") or {}).get("spend_usd"))
        before = (cap - (used["spend_usd"] - last_cost)) if cap else None
        cost_share = last_cost / before if before and before > 0 else 0.0
        time_cap = number((history.get("ceiling") or {}).get("seconds"))
        if time_cap:
            cost_share = max(cost_share, (number(last.get("seconds")) or 0.0) / max(time_cap - (used["seconds"] - (number(last.get("seconds")) or 0.0)), 1e-9))
        facts = dict(facts, gain_share=round(share, 4), cost_share=round(cost_share, 4))
        if share < MIN_GAIN_SHARE:
            return result(STOP_NOT_WORTH_IT, "plateau", "the last iteration closed too little of the gap to earn another", facts, left)
        if share < cost_share:
            return result(STOP_NOT_WORTH_IT, "cost_exceeds_gain", "the last iteration cost a larger share of what remains than the share of the gap it closed", facts, left)
        return result(CONTINUE, "gain_worth_cost", "the last iteration closed a worthwhile share of the gap for its cost", facts)
    changed = number(last.get("changed")) or 0
    first_cost = (max(shares[k] for k in shares if shares[k] is not None)) if any(v is not None for v in shares.values()) else 0.0
    if not changed:
        return result(STOP_NOT_WORTH_IT, "plateau", "the first iteration changed nothing", facts, left)
    if first_cost >= FIRST_COST_SHARE:
        return result(STOP_NOT_WORTH_IT, "cost_exceeds_gain", "the first iteration cost half or more of the budget and showed no gain to justify a second", facts, left)
    return result(CONTINUE, "first_progress", "the first iteration changed things and cost little of the budget", facts)


def selected_stop_decider() -> Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]]:
    """The ``decide_stop`` of the hub's selected Goal Completion implementation, resolved by name from the records (the way Folder View is resolved), or None when none can
    be assembled here: a caller then keeps its deterministic default. Delegation and the runners of Delegated Agent Sessions ask the decision through this."""
    try:
        from esoi import selection
        return selection.resolve("goal-completion", scope="hubofhubs")().decide_stop
    except Exception:  # noqa: BLE001 -- no arm, a missing key or a broken install is no stop decision, never a failed run
        return None


def fixed_cap(history: Mapping[str, Any], cap: int = FIXED_CAP) -> Dict[str, Any]:
    """The baseline: a fixed number of iterations, whatever else is true (stop met only when the last verdict says so)."""
    its = iterations_of(history)
    if its and verdict_of(its[-1]):
        return result(STOP_MET, "met", "the last verdict is met", {"iterations": len(its)})
    if len(its) >= cap:
        return result(STOP_GOOD_ENOUGH, "cap", f"{cap} iterations are the fixed cap", {"iterations": len(its)}, what_is_left(history))
    return result(CONTINUE, "under_cap", "fewer iterations than the cap", {"iterations": len(its)})


def until_met(history: Mapping[str, Any], verdict: Optional[bool] = None) -> Dict[str, Any]:
    """The baseline: stop only when the goal is met, never otherwise."""
    its = iterations_of(history)
    met = (verdict_of(its[-1]) if its else False) if verdict is None else verdict
    if met:
        return result(STOP_MET, "met", "the last verdict is met", {"iterations": len(its)})
    return result(CONTINUE, "not_met", "the goal is not met", {"iterations": len(its)})


def history_from_facts(facts: Mapping[str, Any], *, goal: str = "", done_standard: str = "", stated: Optional[Mapping[str, Any]] = None,
                       policy: Optional[Mapping[str, Any]] = None, milestone: Optional[Mapping[str, Any]] = None,
                       iterations: Sequence[Mapping[str, Any]] = ()) -> Dict[str, Any]:
    """An iteration history from the plain facts a runner holds (``spend_usd``, ``elapsed_seconds``, the ceilings, ``findings``) for the iterations it
    has made, each as its own record. The runner's fallback when it has no per-iteration record: one record per iteration with what it knows."""
    return {"goal": goal, "done_standard": done_standard, "iterations": [dict(i) for i in iterations],
            "ceiling": {"spend_usd": facts.get("ceiling_usd"), "seconds": facts.get("ceiling_seconds"), "soft_fraction": facts.get("soft_fraction") or SOFT_FRACTION},
            "stated": dict(stated or {}), "policy": dict(policy or {}), "milestone": dict(milestone or {})}
