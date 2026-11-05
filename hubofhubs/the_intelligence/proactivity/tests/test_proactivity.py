"""Proactivity as a foundation: typed triggers, events a consumer pulled through Intake Sources, and the due work in the order Prioritization gives."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import hubofhubs  # noqa: E402
from hubofhubs.api import TRIGGER_KINDS, attach_events, candidate_of, in_priority_order  # noqa: E402
from hubofhubs.the_intelligence.proactivity.triggers import CalendarAndEvents, ElapsedHours  # noqa: E402

NOW = "2026-07-12T09:00:00Z"


def test_each_trigger_says_why_it_is_due_by_kind():
    arm = CalendarAndEvents()
    got = {t["schedule"]: t["kind"] for t in arm.due([
        {"name": "asked", "cadence": "daily", "last_run": "2026-07-12T08:00:00Z", "run_requested_at": "2026-07-12T08:30:00Z"},
        {"name": "reacts", "reactive": True, "last_run": "2026-07-01T00:00:00Z", "events": ["2026-07-05T00:00:00Z"]},
        {"name": "weekly", "cadence": "weekly", "last_run": "2026-07-01T09:00:00Z"}], NOW)}
    assert got == {"asked": "requested", "reacts": "event", "weekly": "period"} and set(got.values()) <= set(TRIGGER_KINDS)
    assert ElapsedHours().due([{"name": "e", "cadence": "daily"}], NOW)[0]["kind"] == "elapsed"


def test_events_pulled_from_intake_sources_make_the_schedule_that_names_the_source_due():
    schedules = [{"name": "s", "event_source": "quest-events", "last_run": "2026-07-01T00:00:00Z"}]
    pulled = [{"source": "quest-events", "at": "2026-07-05T00:00:00Z"}, {"source": "other", "at": "2026-07-06T00:00:00Z"}, {"source": "quest-events", "at": "junk"}]
    assert attach_events(schedules, pulled)[0]["events"] == ["2026-07-05T00:00:00Z"] and "events" not in schedules[0]
    assert [t["schedule"] for t in CalendarAndEvents().due(attach_events(schedules, pulled), NOW)] == ["s"]
    assert CalendarAndEvents().due(attach_events(schedules, pulled[1:]), NOW) == []


def test_the_entry_takes_a_prioritization_answer_and_returns_the_due_work_in_its_order():
    schedules = [{"name": "a", "request": "ra", "cadence": "weekly", "horizon": "week"}, {"name": "b", "request": "rb", "cadence": "weekly", "horizon": "today"},
                 {"name": "c", "request": "rc", "cadence": "weekly"}]
    seat = hubofhubs.run("prioritization", {"candidates": [candidate_of({"schedule": s["name"], "request": s["request"]}, schedules) for s in schedules], "now": NOW,
                                           "stated": {"not_before": {"c": "2027-01-01T00:00:00Z"}}})
    got = hubofhubs.run("proactivity", {"schedules": schedules, "now": NOW, "priorities": seat})
    assert [(t["schedule"], t["rank"]) for t in got] == [("b", 1), ("a", 2)]      # c is held back; the others keep their reasons
    assert got[0]["request"] == "rb" and got[0]["kind"] == "period" and got[0]["priority_reason"]


def test_without_an_answer_the_triggers_come_back_as_they_were_and_a_due_trigger_it_did_not_mention_follows():
    triggers = [{"schedule": "a", "kind": "period", "reason": "r", "request": "x"}]
    assert in_priority_order(triggers, (), None) == triggers
    out = in_priority_order(triggers, (), {"ordered": [], "held": []})
    assert [t["schedule"] for t in out] == ["a"]
