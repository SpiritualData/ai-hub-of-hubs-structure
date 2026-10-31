"""Scores a connect-any-integration arm: each check of one area fact, and the fake-hub probe."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

BASE = dict(registered=True, config_ok=True, fresh=True, seam=True, selectable=True, vendor_branches=[], reinvented=[], waived=0,
            days=3, status="ok", capabilities=2, by_config=2, arm_gaps=[], probe=None)


def adapt(implementation, meter):
    def run(kind, args):
        fact = dict(BASE, **args.get("fact", {}))
        if "probe" in args:
            behaviour = args["probe"]

            def probe():
                if behaviour == "raises":
                    raise RuntimeError("no config path")
                return (behaviour == "accepts"), "fake hub"
            fact["probe"] = probe if behaviour != "none" else None
        return implementation.check(fact, kind)["holds"]
    return run


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
