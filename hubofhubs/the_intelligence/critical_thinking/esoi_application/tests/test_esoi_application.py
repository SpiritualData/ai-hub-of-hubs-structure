"""ESOI Application edits exactly the field named and a refused change leaves the records as they were."""
from hubofhubs.the_intelligence.critical_thinking.esoi_application.apply import RecordFieldEdit, TableRecords

RECORDS = {"solutions": {"s": {"purpose": "old", "description": "d"}}}


def test_an_edit_sets_the_one_field_and_reports_before_and_after():
    arm = RecordFieldEdit(RECORDS)
    out = arm.apply({"edit": {"kind": "spec_edit", "target": "s", "field": "purpose", "value": "new"}})
    assert out["applied"] and out["before"] == "old" and arm.records["solutions"]["s"] == {"purpose": "new", "description": "d"} and RECORDS["solutions"]["s"]["purpose"] == "old"


def test_a_refused_change_changes_nothing():
    arm = RecordFieldEdit(RECORDS)
    for edit in ({"kind": "spec_edit", "target": "s", "field": "nope", "value": "x"}, {"kind": "spec_edit", "target": "s", "field": "purpose", "value": "a — b"}):
        assert arm.apply({"edit": edit})["applied"] is False
    assert arm.records == RECORDS


class Holding(TableRecords):
    """A records location that holds every edit of the field 'purpose' for approval."""

    def apply(self, edit):
        if edit.get("field") == "purpose":
            return {"status": "proposed", "decision": "d1"}
        return super().apply(edit)


def test_an_addition_is_ensure_one_at_the_default_location():
    arm = RecordFieldEdit({})
    add = {"edit": {"kind": "record_add", "table": "implementations", "key": "post-a", "fields": {"name": "Post A"}}}
    assert arm.apply(add)["created"] is True
    again = arm.apply(add)
    assert again["created"] is False and again["note"] == "already there" and list(arm.records["implementations"]) == ["post-a"]


def test_a_location_of_the_consumer_is_used_and_a_held_edit_is_proposed_not_applied():
    arm = RecordFieldEdit(source=Holding(RECORDS))
    out = arm.apply({"edit": {"kind": "spec_edit", "target": "s", "field": "purpose", "value": "new"}})
    assert out["applied"] is False and out["proposed"] is True and out["decision"] == "d1" and "waiting for approval" in out["reason"]
    assert arm.read("anything")["solutions"]["s"]["purpose"] == "old"
