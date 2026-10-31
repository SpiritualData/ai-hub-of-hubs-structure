"""Scores a reason-and-answer arm: the (provider, model) chosen for a tier from recorded measurements, prices and credits."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    def run(kind, args):
        got = implementation.pick(args["arms"], args["prices"], args.get("credits", ()), args.get("default"),
                                  min_cases=args.get("min_cases", 1), min_pass_rate=args.get("min_pass_rate", 0.0))
        return got["arm"]
    return run


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
