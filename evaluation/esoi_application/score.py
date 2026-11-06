"""Scores an ESOI Application arm: given records and a proposed change, does it apply exactly the edit asked for, to the one field named, and refuse a change that
cannot be applied (unknown target, field or kind, an empty value, an em dash) while leaving every record as it was? One number: the share of cases whose result and
resulting records both equal what the case expects (an arm that appends the change to a description instead of editing the field fails them). Written cases; no
model call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402
from hubofhubs.api import TableRecords  # noqa: E402


class ScriptedLocation(TableRecords):
    """A records location that holds named fields for approval (``holds``) or refuses every write (``denies``), to score how an arm reports what it was told."""

    def __init__(self, records, holds=(), denies=""):
        super().__init__(records)
        self.holds, self.denies = set(holds), denies

    def apply(self, edit):
        if self.denies:
            return {"status": "refused", "reason": self.denies}
        if edit.get("field") in self.holds:
            return {"status": "proposed", "decision": "decision-1", "reason": "the owner has to say yes"}
        return super().apply(edit)


def adapt(implementation, meter):
    def run(kind, args):
        changes = args.get("changes") or [args["change"]]
        scripted = args.get("source")
        try:
            arm = implementation(records=args["records"], source=ScriptedLocation(args["records"], **{"holds": scripted.get("holds", ()), "denies": scripted.get("denies", "")})) if scripted else implementation(records=args["records"])
        except TypeError:     # an arm with no records location of its own cannot be given one
            return {"result": {"applied": False, "reason": "this arm has no records location"}, "records": args["records"]}
        result = None
        for change in changes:
            result = arm.apply(change)
        return {"result": result, "records": arm.records}
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("applies", "refused", "adds", "repeats", "proposed")}
