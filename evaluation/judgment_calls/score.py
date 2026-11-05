"""Scores a Judgment Calls arm: for a risk signal and a person, does it decide to ask, proceed or decline as the case expects?

The signals come from the labelled digests of the Nervous System's case sets (a step a person should authorize is high, an ordinary step is none) and from a
flow that stopped for budget or authority. One number: the share of decisions that match. No model call. The per-person cases are written here; a replay of real
decision requests is not in this set."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    def run(kind, args):
        takes_policies = "policies" in inspect.signature(implementation).parameters
        arm = implementation(policies=args["policies"]) if takes_policies and "policies" in args else implementation()
        return arm.decide(args["signal"], args["person"], args["context"])["decision"]
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("explicit", "ambiguous", "stopped", "person")}
