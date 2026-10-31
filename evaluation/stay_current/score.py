"""Scores a stay-current arm: the age in days of a recorded date, and the share terms of a combined reading."""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    def run(kind, args):
        clock = datetime.date.fromisoformat(args["today"])
        if kind == "days_since":
            return implementation.days_since(args["iso"], clock)
        fact = lambda fresh, registered: dict(days=1, fresh=fresh, registered=registered, seam=True, selectable=True, vendor_branches=[])
        facts = [fact(f, r) for f, r in args["facts"]]
        got = implementation.combine(facts, [])
        return {k: got[k] for k in ("coverage", "fresh_share")}
    return run


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
