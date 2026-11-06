"""Scores a Hands arm: for a system's declared enduring integrations and its recent run records, does it say for each whether the AI can reach it and whether it was
used, and mark the declared but idle ones? One number: the share of cases whose list equals the expected list. A list that only repeats the declaration fails the
cases with an idle or cut off integration. Written declarations and run records; a real system's own are not in this set. No model call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    def run(kind, args):
        return implementation(declared=args["declared"], runs=args["runs"]).integrations(args["system"])
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("declared", "unused", "reach")}
