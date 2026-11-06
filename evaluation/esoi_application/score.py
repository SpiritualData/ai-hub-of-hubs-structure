"""Scores an ESOI Application arm: given records and a proposed change, does it apply exactly the edit asked for, to the one field named, and refuse a change that
cannot be applied (unknown target, field or kind, an empty value, an em dash) while leaving every record as it was? One number: the share of cases whose result and
resulting records both equal what the case expects (an arm that appends the change to a description instead of editing the field fails them). Written cases; no
model call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    def run(kind, args):
        arm = implementation(records=args["records"])
        return {"result": arm.apply(args["change"]), "records": arm.records}
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("applies", "refused")}
