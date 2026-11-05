"""Scores a Goal Completion arm: for a goal, a done-standard and an outcome, does the arm say whether the goal was met as the case expects?

The coverage cases are the ones the done-evidence tests assert; the others are an empty outcome, a refused one and a done-standard whose
requirements the outcome holds or misses. One number: the share of cases answered correctly. No model call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    arm = implementation()
    return lambda kind, args: bool(arm.check(args["goal"], args["done_standard"], args["outcome"])["met"])


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])
