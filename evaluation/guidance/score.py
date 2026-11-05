"""Scores a Guidance arm, two sided: when a nudge is due, is it one grounded sentence about the right objective; when it is not, does the arm say nothing?

A nudge case passes when the arm points at the expected objective, in one sentence with no dash, that holds the objective's next target and reading as the objective
states them (nothing invented). A restraint case passes when the arm returns nothing. The cases hold as many of each, so the share answered correctly is the mean of the
nudge pass rate and the restraint pass rate. No model call, no network."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

DASHES = ("—", "–", " -- ")


def adapt(implementation, meter):
    arm = implementation()
    return lambda kind, args: arm.nudge(args["request"], args["objectives"])


def grounded(got, objective):
    text = got["nudge"]
    reading = str(objective.get("reading") or "").rstrip(".")
    return (objective["next_target"].rstrip(".") in text and reading in text and not any(d in text for d in DASHES)
            and len(re.findall(r"[.!?](?:\s|$)", text.strip())) <= 1)


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    want = case["expect"]
    if want is None:
        return dict(judge(got is None, dict(case, expect=True)), kind=case["kind"], side="restraint")
    objective = next(o for o in case["args"]["objectives"] if o["id"] == want)
    ok = bool(got) and got.get("objective") == want and grounded(got, objective)
    return dict(ok=ok, got=str(got)[:60], note="" if ok else f"expected a grounded nudge for {want}", kind=case["kind"], side="nudge")


def aggregate(rows):
    def rate(side):
        part = [r for r in rows if r.get("side") == side]
        return round(sum(bool(r["ok"]) for r in part) / max(len(part), 1), 4)
    return {"nudge_pass_rate": rate("nudge"), "restraint_pass_rate": rate("restraint")}
