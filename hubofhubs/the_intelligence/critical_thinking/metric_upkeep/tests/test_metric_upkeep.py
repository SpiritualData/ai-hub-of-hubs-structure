"""Metric Upkeep on generic records: states from fields, a read recorded, and one intermediate metric added only after an independent check agrees."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.critical_thinking.decision_check.agreement import MajorityVote  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.esoi_application.apply import RecordFieldEdit  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.metric_upkeep.upkeep import (  # noqa: E402
    DEFINE_INTERMEDIATE, FRESH, NO_SOURCE, NONE, PROPOSE_SOURCE, READ, STALE, UNMEASURED, RecordFieldUpkeep, state_of, day_of)

TODAY = "2030-03-10"
SPEC = {"solution_id": "sol-a", "name": "Launch tutorials published", "done_when": "Six tutorials are published", "moved_by": "person"}


def records(**metric):
    return {"solutions": {"sol-a": {"name": "Launch tutorials published", "milestones": "Six tutorials are published"}},
            "metrics": {"m-pub": dict({"name": "Tutorials published", "record": "Current value: 0 of 6", "solution_ids": ["sol-a"]}, **metric)}}


def arm(tables):
    esoi = RecordFieldEdit(tables)
    return RecordFieldUpkeep(esoi=esoi, decision=MajorityVote(plumbing=None)), esoi


def model(track="tracks"):
    """A scripted cheap model: one proposal, and each view's pick quoting its evidence."""
    def ask(prompt):
        if "Propose ONE intermediate metric" in prompt:
            return json.dumps({"name": "Tutorial scripts meeting the rubric", "definition": "Count the tutorial scripts that meet every rubric item.",
                               "unit": "scripts", "total": 6, "feeds_parent": "Each published tutorial needs a script that meets the rubric first.",
                               "rubric": ["has an opening", "has a call to action"]})
        return json.dumps({"pick": track, "quote": "Proposed intermediate metric"})
    return ask


def test_state_is_decided_from_fields_alone():
    day = day_of(TODAY)
    assert state_of({"source": ""}, day) == NO_SOURCE
    assert state_of({"source": "sheet"}, day) == UNMEASURED
    assert state_of({"record": "Current value: 3", "measured_through": "2030-03-01", "expiration": "weekly"}, day) == STALE
    assert state_of({"record": "Current value: 3", "measured_through": "2030-03-09", "expiration": 7}, day) == FRESH
    assert state_of({"record": "Current value: 3", "measured_through": "2020-01-01"}, day) == FRESH       # no expiration: never stale


def test_a_stale_metric_with_a_reader_is_read_and_recorded_through_esoi_application():
    tables = records(source="sheet", measured_through="2030-01-01", expiration="weekly")
    upkeep, esoi = arm(tables)
    actions = upkeep.upkeep(dict(SPEC, moved_by="ai"), tables["metrics"], {"sheet": lambda mid: {"value": 2, "as_of": "2030-03-09", "source": "the sheet"}}, TODAY)
    assert actions[0]["action"] == READ and actions[0]["state"] == STALE
    assert esoi.records["metrics"]["m-pub"]["record"] == "Current value: 2 (as of 2030-03-09, from the sheet)"


def test_no_source_is_reported_pending_never_guessed():
    tables = records(record="")
    upkeep, _ = arm(tables)
    actions = upkeep.upkeep(dict(SPEC, moved_by="ai"), tables["metrics"], None, TODAY)
    assert actions[0]["state"] == NO_SOURCE and actions[0]["action"] == PROPOSE_SOURCE and actions[0]["proposed_source"] is None


def test_a_person_moved_metric_gets_one_intermediate_after_agreement_and_none_on_repeat():
    tables = records()
    upkeep, esoi = arm(tables)
    first = upkeep.upkeep(SPEC, tables["metrics"], None, TODAY, model())[0]
    child = first["child_metric"]
    assert first["action"] == DEFINE_INTERMEDIATE and child["created"] and child["parent_metric_ids"] == ["m-pub"] and child["total"] == "6"
    assert child["id"] in esoi.records["metrics"] and esoi.records["metrics"][child["id"]]["cascading_conditionals"].startswith("feeds m-pub")
    again = upkeep.upkeep(SPEC, esoi.records["metrics"], None, TODAY, model())
    assert len(again) == 1 and again[0]["child_metric"]["created"] is False       # the child is reused, never a second, and is not upkept as a milestone metric itself
    assert len([m for m in esoi.records["metrics"].values() if "m-pub" in (m.get("parent_metric_ids") or [])]) == 1


def test_no_intermediate_is_added_when_the_check_does_not_agree():
    tables = records()
    upkeep, esoi = arm(tables)
    action = upkeep.upkeep(SPEC, tables["metrics"], None, TODAY, model(track="does_not_track"))[0]
    assert action["child_metric"] is None and "did not agree" in action["why"]
    assert list(esoi.records["metrics"]) == ["m-pub"]


def test_an_ai_moved_metric_that_is_fresh_needs_nothing():
    tables = records(measured_through="2030-03-09")
    upkeep, _ = arm(tables)
    assert upkeep.upkeep(dict(SPEC, moved_by="ai"), tables["metrics"], None, TODAY)[0]["action"] == NONE


def test_unmeasured_without_a_reader_stays_unmeasured():
    tables = records(record="", source="sheet")
    upkeep, _ = arm(tables)
    action = upkeep.upkeep(dict(SPEC, moved_by="ai"), tables["metrics"], None, TODAY)[0]
    assert action["state"] == UNMEASURED and action["action"] == NONE
