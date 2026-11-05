"""Rebuild cases.json for Proactivity from the cadence and request cases a production autopilot's own tests assert (the clock there is Sunday
2026-07-12 09:00 UTC): never run is due, a weekly schedule is not due in the same ISO week and is due in a later one, a daily schedule is due on a new
calendar day even 17 hours after a late run, monthly is once per calendar month, the year boundary compares the year with the month or week, an
unreadable time fails open to due, an evening run is read in its own zone, a run requested after the last run is due, and a reactive schedule is due
only for an event after the last run.

    python3 evaluation/proactivity/build_cases.py

``expect`` is the names of the schedules due. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-07-12T09:00:00Z"


def case(name, schedule, expect, now=NOW):
    return {"id": "proactive-" + name, "kind": "schedule", "args": {"schedules": [dict(schedule, name="s", request="do the standing work")], "now": now}, "expect": ["s"] if expect else []}


def main():
    cases = [
        case("never-run", {"cadence": "weekly"}, True),
        case("weekly-same-week", {"cadence": "weekly", "last_run": "2026-07-10T09:00:00Z"}, False),
        case("weekly-later-week", {"cadence": "weekly", "last_run": "2026-07-01T09:00:00Z"}, True),
        case("daily-late-yesterday", {"cadence": "daily", "last_run": "2026-07-11T16:11:00Z"}, True),
        case("daily-already-today", {"cadence": "daily", "last_run": "2026-07-12T08:00:00Z"}, False),
        case("monthly-last-month", {"cadence": "monthly", "last_run": "2026-06-20T09:00:00Z"}, True),
        case("monthly-this-month", {"cadence": "monthly", "last_run": "2026-07-01T09:00:00Z"}, False),
        case("monthly-year-boundary", {"cadence": "monthly", "last_run": "2025-12-31T09:00:00Z"}, True, "2026-01-01T09:00:00Z"),
        case("weekly-year-boundary", {"cadence": "weekly", "last_run": "2025-12-29T09:00:00Z"}, True, "2026-01-05T09:00:00Z"),
        case("unreadable-time-fails-open", {"cadence": "weekly", "last_run": "not-a-date"}, True),
        case("evening-run-in-its-own-zone", {"cadence": "daily", "zone": "America/Los_Angeles", "last_run": "2026-08-21T05:00:00Z"}, True, "2026-08-21T20:00:00Z"),
        case("run-requested-after-last-run", {"cadence": "daily", "last_run": "2026-07-12T08:00:00Z", "run_requested_at": "2026-07-12T08:55:00Z"}, True),
        case("run-requested-before-last-run", {"cadence": "daily", "last_run": "2026-07-12T08:00:00Z", "run_requested_at": "2026-07-12T07:00:00Z"}, False),
        case("reactive-event-after-last-run", {"reactive": True, "last_run": "2026-07-01T00:00:00Z", "events": ["2026-07-05T00:00:00Z"]}, True),
        case("reactive-event-before-last-run", {"reactive": True, "last_run": "2026-07-01T00:00:00Z", "events": ["2026-06-20T00:00:00Z"]}, False),
        case("reactive-never-run-with-event", {"reactive": True, "events": ["2026-01-01T00:00:00Z"]}, True),
        case("reactive-never-run-no-event", {"reactive": True, "events": []}, False),
        case("reactive-unreadable-events-ignored", {"reactive": True, "last_run": "2026-07-01T00:00:00Z", "events": [None, "not a date"]}, False),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
