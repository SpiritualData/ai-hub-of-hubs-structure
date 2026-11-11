"""The stages of the authoritative metric that the cascade grammar cannot hold, as one pure rule: which arm is selectable and which one the metric selects.

The cascade of ``metric-delegated-agent-sessions-hard`` (esoi's grammar) orders the cheap proofs and ranks arms by the balanced number on the hard set.
Four conditions sit beyond what that grammar can express because they read more than one component or more than one run; they are written here, fixed
before any arm was scored on them, and read by ``arm_choice`` and by the test that pins the record's ``selected`` to them:

1. ``open_ended``: the mean pass rate of the arm's counting whole runs of the open-ended set is at least ``OPEN_FLOOR`` (17 of 18).
2. ``hard``: the mean pass rate of its counting whole runs of the hard set is at least ``HARD_FLOOR`` (6 of 9: the six coding cases are checked by hidden
   tests and must all pass; the three judged deliverables vary from run to run and are decided by the repeated runs of stage 3, not by a floor).
3. ``repeated``: at least ``MIN_RUNS`` counting hard runs, so that a difference can be told from noise. When no arm has them the stage is not run and
   skips; an arm with fewer runs than another arm has stays selectable only until an arm with enough runs exists.
3b. ``depth``: the depth set (``evaluation/agent_sessions_depth``), after ``repeated``. When any arm has at least ``MIN_RUNS`` counting depth runs, every
   arm needs that many and a pooled pass rate of at least ``DEPTH_FLOOR``; when no arm has them the stage skips. When every contender has depth runs,
   cost and seconds per case for the tie-break are those of the hard and depth sets added, so sub-agent overuse on the small case costs.
4. ``real_task``: a recorded run of a consumer's own deep task, with its outcome. When no arm has one the stage is not run and skips.

Among the selectable arms the metric picks the one whose pooled hard pass rate is highest, then every arm whose pass rate is not significantly lower
(two-sided exact Fisher test on the pooled passed and failed cases of the counting runs, ``ALPHA``) and lower by less than one case per run (the unit
the weights protect, so two cases of nine are never noise) is a contender, and among contenders cost per case decides, then seconds per case: pass rate dominates, and cost and time break ties within noise. An arm that needs a credential the install lacks is
left out by the caller (``arm_choice.eligible``) before this rule runs. No model call and no environment read; plain rows in, a verdict out."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import comb
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

OPEN_FLOOR = 0.94
HARD_FLOOR = 0.66
DEPTH_FLOOR = 0.8   # four of the five depth cases (evaluation/agent_sessions_depth), all scored by code; fixed before any arm was scored on them
MIN_RUNS = 3
ALPHA = 0.05
STAGES = ("open_ended", "hard", "repeated", "depth", "real_task")


def number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def pooled(rows: Sequence[Mapping[str, Any]]) -> Tuple[int, int]:
    """``(passed, cases)`` summed over the runs."""
    return sum(int(number(r.get("passed"))) for r in rows), sum(int(number(r.get("cases"))) for r in rows)


def rate(rows: Sequence[Mapping[str, Any]]) -> float:
    passed, cases = pooled(rows)
    return passed / cases if cases else 0.0


def per_case(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    cases = pooled(rows)[1]
    return sum(number(r.get(key)) for r in rows) / cases if cases else float("inf")


def fisher_two_sided(a_pass: int, a_all: int, b_pass: int, b_all: int) -> float:
    """The two-sided exact Fisher p-value of two pass counts (the sum of the tables no likelier than the one seen)."""
    total, passes = a_all + b_all, a_pass + b_pass

    def chance(k: int) -> float:
        return comb(passes, k) * comb(total - passes, a_all - k) / comb(total, a_all)
    seen = chance(a_pass)
    low, high = max(0, a_all - (total - passes)), min(a_all, passes)
    return min(1.0, sum(p for p in (chance(k) for k in range(low, high + 1)) if p <= seen * (1 + 1e-9)))


@dataclass
class Verdict:
    """What the metric says: the arm it selects (empty when none is selectable) and, for every arm, how far it got and why it stopped."""
    winner: str = ""
    reason: str = ""
    stages: Dict[str, Dict[str, str]] = field(default_factory=dict)   # {arm: {stage: "passed ..." | "stopped: ..." | "not run"}}


def stage_report(arm: str, open_rows: Sequence[Mapping[str, Any]], hard_rows: Sequence[Mapping[str, Any]], real_rows: Sequence[Mapping[str, Any]],
                 repeat_needed: bool, depth_rows: Sequence[Mapping[str, Any]] = (), depth_needed: bool = False) -> Tuple[bool, Dict[str, str]]:
    """``(selectable, {stage: outcome})`` of one arm; the first failed floor ends its report."""
    out: Dict[str, str] = {}
    if not open_rows or rate(open_rows) < OPEN_FLOOR:
        out["open_ended"] = "not run" if not open_rows else f"stopped: pass rate {rate(open_rows):.3f} is below the floor {OPEN_FLOOR}"
        return False, out
    out["open_ended"] = "passed " + "{}/{}".format(*pooled(open_rows))
    if not hard_rows or rate(hard_rows) < HARD_FLOOR:
        out["hard"] = "not run" if not hard_rows else f"stopped: pass rate {rate(hard_rows):.3f} is below the floor {HARD_FLOOR}"
        return False, out
    out["hard"] = "passed {}/{} over {} run(s)".format(*pooled(hard_rows), len(hard_rows))
    if repeat_needed and len(hard_rows) < MIN_RUNS:
        out["repeated"] = f"stopped: {len(hard_rows)} counting hard run(s), {MIN_RUNS} needed"
        return False, out
    out["repeated"] = f"passed ({len(hard_rows)} runs)" if repeat_needed else "not run (no arm has enough runs yet)"
    if depth_needed and len(depth_rows) < MIN_RUNS:
        out["depth"] = f"stopped: {len(depth_rows)} counting depth run(s), {MIN_RUNS} needed"
        return False, out
    if depth_needed and rate(depth_rows) < DEPTH_FLOOR:
        out["depth"] = f"stopped: pass rate {rate(depth_rows):.3f} is below the floor {DEPTH_FLOOR}"
        return False, out
    out["depth"] = "passed {}/{} over {} run(s)".format(*pooled(depth_rows), len(depth_rows)) if depth_needed else "not run (no arm has enough runs yet)"
    if real_rows and not all(str(r.get("ok", "1")) in ("1", "True", "true") for r in real_rows):
        out["real_task"] = "stopped: a recorded real task failed"
        return False, out
    out["real_task"] = "passed" if real_rows else "not run (no arm has one)"
    return True, out


def decide(open_runs: Mapping[str, Sequence[Mapping[str, Any]]], hard_runs: Mapping[str, Sequence[Mapping[str, Any]]],
           real_runs: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None, arms: Optional[Sequence[str]] = None,
           depth_runs: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None) -> Verdict:
    """The metric's selection among ``arms`` (default every arm with a run), from each arm's counting whole runs of the open-ended set, of the hard set and
    its real-task results, all on the current cases."""
    real_runs = real_runs or {}
    depth_runs = depth_runs or {}
    names = sorted(set(arms) if arms is not None else set(open_runs) | set(hard_runs))
    repeat_needed = any(len(hard_runs.get(a, ())) >= MIN_RUNS for a in names)
    depth_needed = any(len(depth_runs.get(a, ())) >= MIN_RUNS for a in names)
    verdict = Verdict()
    selectable: List[str] = []
    for arm in names:
        ok, report = stage_report(arm, open_runs.get(arm, ()), hard_runs.get(arm, ()), real_runs.get(arm, ()), repeat_needed,
                                  depth_runs.get(arm, ()), depth_needed)
        verdict.stages[arm] = report
        if ok:
            selectable.append(arm)
    if not selectable:
        verdict.reason = "no arm is selectable: every arm stopped at a floor or has not run a stage"
        return verdict
    leader = max(selectable, key=lambda a: (rate(hard_runs[a]), -per_case(hard_runs[a], "cost_usd"), a))
    lp, ln = pooled(hard_runs[leader])
    band = 1.0 / (ln / len(hard_runs[leader]))   # less than one case per run is within noise, the same unit the weights protect
    contenders = [a for a in selectable if a == leader or (rate(hard_runs[leader]) - rate(hard_runs[a]) < band
                                                          and fisher_two_sided(lp, ln, *pooled(hard_runs[a])) >= ALPHA)]
    with_depth = depth_needed and all(depth_runs.get(a) for a in contenders)   # overuse on the depth set shows as cost, so it counts when every contender ran it

    def spend(a: str, key: str) -> float:
        return per_case(hard_runs[a], key) + (per_case(depth_runs[a], key) if with_depth else 0.0)
    verdict.winner = min(contenders, key=lambda a: (spend(a, "cost_usd"), spend(a, "seconds"), a))
    if verdict.winner == leader:
        verdict.reason = (f"highest pooled hard pass rate {rate(hard_runs[leader]):.3f} over {len(hard_runs[leader])} run(s)"
                          + (f"; {len(contenders) - 1} other arm(s) not significantly lower and none cheaper" if len(contenders) > 1 else ""))
    else:
        verdict.reason = (f"{leader} has the highest pooled hard pass rate ({rate(hard_runs[leader]):.3f}); {verdict.winner} is not significantly lower "
                          f"(Fisher p >= {ALPHA}) and is cheaper per case, so cost decides within noise")
    return verdict
