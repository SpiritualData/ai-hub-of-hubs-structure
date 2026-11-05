"""Scores a Proactivity arm: given standing schedules and the time, are exactly the schedules that are due named?

The cases are the cadence, run-request and reactive-event cases a production autopilot's own tests assert. One number: the share of cases with exactly the
right schedules. No model call, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    arm = implementation()
    return lambda kind, args: [t["schedule"] for t in arm.due(args["schedules"], args["now"])]


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
