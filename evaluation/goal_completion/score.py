"""Scores a Goal Completion arm on two stages: does it say whether a goal was met, and does it say when to stop iterating?

Stage ``outcome`` (14 cases): for a goal, a done-standard and an outcome, does the arm say whether the goal was met as the case expects?
Stage ``stop`` (``build_cases.py``): for an iteration history, does ``decide_stop`` return the decision the case expects (continue, stop_met, stop_good_enough,
stop_not_worth_it, ask)? Both errors are scored separately and in the balance, and the weights were fixed before any arm was scored:

* over-iteration: the arm said continue where the right decision was a stop or an ask (spend wasted after the right stop), penalty 1.0;
* premature stop: the arm stopped (any stop) where the right decision was continue (value left that was worth its cost), penalty 1.0;
* wrong ask: the arm asked where it should not have, or did not ask where it should (a person's attention wasted, or a human-only step iterated on), penalty 1.0;
* right action, wrong kind of stop (stop_met for stop_good_enough, and so on): the spend and the iteration are the same, the report to the person differs, penalty 0.5.

Neither error is worth more than the other: over-iteration burns money and time the person did not choose to spend, and a premature stop leaves value that was worth
its cost, and the owner's concern is both. Each case's credit is ``1 - penalty`` (``score`` on the row), so the balanced score (accuracy as the mean credit, with the
cost and time terms of ``[balance.goal_completion]``) carries all four. ``details`` also reports each error as a rate of the cases where it can happen, so an arm
that always continues or always stops cannot hide behind the case mix. No model call for the free arms."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

PENALTY = {"over_iteration": 1.0, "premature_stop": 1.0, "wrong_ask": 1.0, "wrong_stop_kind": 0.5}   # fixed before scoring; recorded in metrics.csv
STOPS = ("stop_met", "stop_good_enough", "stop_not_worth_it")


def adapt(implementation, meter):
    import inspect
    arm = implementation(plumbing=None) if "plumbing" in inspect.signature(implementation).parameters else implementation()

    def run(kind, args):
        if kind == "stop":
            return str(arm.decide_stop(args["history"])["decision"])
        return bool(arm.check(args["goal"], args["done_standard"], args["outcome"])["met"])
    return run


def error_of(got, want):
    """The kind of error ``got`` is against ``want`` ('' when right)."""
    if got == want:
        return ""
    if got == "continue":
        return "over_iteration"
    if want == "continue":
        return "premature_stop" if got in STOPS else "wrong_ask"
    if (got == "ask") != (want == "ask"):
        return "wrong_ask"
    return "wrong_stop_kind"


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    row = dict(judge(got, case), kind=case["kind"])
    if case["kind"] != "stop":
        return dict(row, score=1.0 if row["ok"] else 0.0)
    error = error_of(got, case["expect"])
    return dict(row, error=error, want=case["expect"], score=1.0 - PENALTY.get(error, 0.0))


def aggregate(rows):
    stops = [r for r in rows if r.get("kind") == "stop"]
    out = {f"{kind}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == kind)}/{sum(r.get('kind') == kind for r in rows)}" for kind in sorted({r.get("kind") for r in rows})}

    def rate(error, pool):
        return round(sum(r["error"] == error for r in pool) / max(len(pool), 1), 4)
    out["over_iteration"] = rate("over_iteration", [r for r in stops if r["want"] != "continue"])
    out["premature_stop"] = rate("premature_stop", [r for r in stops if r["want"] == "continue"])
    out["wrong_ask"] = rate("wrong_ask", stops)
    out["wrong_stop_kind"] = rate("wrong_stop_kind", [r for r in stops if r["want"] in STOPS])
    out["stop_credit"] = round(sum(r["score"] for r in stops) / max(len(stops), 1), 4)
    return out
