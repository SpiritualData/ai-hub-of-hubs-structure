"""ESOI Application edits exactly the field named and a refused change leaves the records as they were."""
from hubofhubs.the_intelligence.critical_thinking.esoi_application.apply import RecordFieldEdit

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
