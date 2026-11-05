"""Rebuild cases.json for Proactivity. Two families, reported separately (the ``kind`` of a case), each tagged with its ``origin``.

``schedule`` cases: standing cadence, request and event rules (the clock is Sunday 2026-07-12 09:00 UTC): never run is due, a weekly schedule is not due in the same ISO week and is due in a later one, a daily schedule is due on a new
calendar day even 17 hours after a late run, monthly is once per calendar month, the year boundary compares the year with the month or week, an
unreadable time fails open to due, an evening run is read in its own zone, a run requested after the last run is due, and a reactive schedule is due
only for an event after the last run.

``window`` cases: invented, neutral cases for a schedule with a window (days, run_time, time_zone, grace_minutes): the weekday, before and after the time of day,
the end of the grace window (inclusive), a run already made in the occasion or only before it opened, the same instant in different time zones, a local date that
differs from the UTC date, a grace window that crosses midnight or a day, a requested run outside the window, and the clock changes (a local time that does not exist,
one that happens twice, and the wall clock kept across the change). The expected answer is written by hand from the rule, never produced by an arm.

    python3 evaluation/proactivity/build_cases.py

``expect`` is the names of the schedules due. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-07-12T09:00:00Z"


def case(name, schedule, expect, now=NOW, kind="schedule", origin="rule: standing cadence, request and event rules"):
    return {"id": "proactive-" + name, "kind": kind, "origin": origin, "args": {"schedules": [dict(schedule, name="s", request="do the standing work")], "now": now}, "expect": ["s"] if expect else []}


def window_case(name, rule, expect, now, last_run="", requested="", **window):
    fields = {"days": ["mon", "tue", "wed", "thu", "fri"], "run_time": "09:00", "time_zone": "America/New_York", "grace_minutes": 60}
    fields.update(window)
    extra = {"window": fields}
    if last_run:
        extra["last_run"] = last_run
    if requested:
        extra["run_requested_at"] = requested
    return case("window-" + name, extra, expect, now, kind="window", origin="rule: " + rule)


def window_cases():
    return [
        window_case("weekday-open", "a chosen day is due once its local time of day has arrived (09:30 in New York)", True, "2026-07-13T13:30:00Z"),
        window_case("before-the-time", "not due before the local time of day (08:30 in New York)", False, "2026-07-13T12:30:00Z"),
        window_case("not-a-chosen-day", "not due on a day that is not chosen (a Sunday)", False, "2026-07-12T13:30:00Z"),
        window_case("grace-ended", "not due once the grace window has ended (11:00 with 60 minutes)", False, "2026-07-13T15:00:00Z"),
        window_case("grace-end-is-inclusive", "due at the last minute of the grace window", True, "2026-07-13T14:00:00Z"),
        window_case("zero-grace-at-the-time", "with no grace, due only at the minute of the time of day", True, "2026-07-13T13:00:00Z", grace_minutes=0),
        window_case("zero-grace-a-minute-later", "with no grace, not due a minute later", False, "2026-07-13T13:01:00Z", grace_minutes=0),
        window_case("already-ran-in-the-occasion", "once in each occasion: a run after it opened covers it", False, "2026-07-13T13:30:00Z", last_run="2026-07-13T13:05:00Z"),
        window_case("ran-the-day-before", "a run on an earlier occasion does not cover this one", True, "2026-07-14T13:30:00Z", last_run="2026-07-13T13:05:00Z"),
        window_case("ran-before-it-opened", "a run earlier the same day, before the time of day, does not cover the occasion", True, "2026-07-13T13:30:00Z", last_run="2026-07-13T12:00:00Z"),
        window_case("missed-days-are-not-owed", "days missed are not run later: only the open occasion counts", True, "2026-07-15T13:30:00Z", last_run="2026-07-13T13:05:00Z"),
        window_case("grace-longer-than-a-day", "a grace window longer than a day keeps the occasion open into the next day", True, "2026-07-14T13:30:00Z", days=["mon"], grace_minutes=2000),
        window_case("time-zone-not-yet", "the same instant is read in the schedule's own zone (22:30 in Tokyo, before 23:00)", False, "2026-07-13T13:30:00Z", time_zone="Asia/Tokyo", run_time="23:00"),
        window_case("time-zone-open", "the same instant is due in a zone where the time of day has arrived (22:30 in Tokyo, from 22:00)", True, "2026-07-13T13:30:00Z", time_zone="Asia/Tokyo", run_time="22:00"),
        window_case("local-day-after-the-utc-day", "the day is the local day: Monday evening in Los Angeles is already Tuesday in UTC", True, "2026-07-14T03:30:00Z",
                    days=["mon"], time_zone="America/Los_Angeles", run_time="20:00"),
        window_case("local-day-before-the-utc-day", "a Tuesday in UTC that is still Monday locally is not a Tuesday occasion", False, "2026-07-14T03:30:00Z",
                    days=["tue"], time_zone="America/Los_Angeles", run_time="20:00"),
        window_case("grace-crosses-midnight", "the occasion keeps its own day when the grace window crosses midnight (00:15 Saturday for a Friday 23:30 start)", True, "2026-07-17T22:15:00Z",
                    days=["fri"], time_zone="Europe/Paris", run_time="23:30", grace_minutes=120),
        window_case("midnight-grace-ended", "the same window closes after its grace (02:00 Saturday)", False, "2026-07-18T00:00:00Z",
                    days=["fri"], time_zone="Europe/Paris", run_time="23:30", grace_minutes=120),
        window_case("requested-outside-the-window", "a run requested after the last run is due whatever the window", True, "2026-07-12T13:30:00Z", last_run="2026-07-10T13:05:00Z", requested="2026-07-12T12:00:00Z"),
        window_case("dst-wall-clock-kept", "after the clocks go forward the time of day is still the local one (09:30 EDT on the first Monday after)", True, "2026-03-09T13:30:00Z"),
        window_case("dst-wall-clock-grace-ended", "and the grace window ends an hour after it in local time (10:30 EDT)", False, "2026-03-09T14:30:00Z"),
        window_case("dst-missing-time-not-yet", "a local time the clocks jump over (02:30 on the spring change) has not opened before the jump", False, "2026-03-08T06:59:00Z",
                    days=["sun"], run_time="02:30"),
        window_case("dst-missing-time-opens-after-the-jump", "it opens when the clock passes it (03:45 after the jump)", True, "2026-03-08T07:45:00Z", days=["sun"], run_time="02:30"),
        window_case("dst-repeated-time-first-pass", "a local time that happens twice opens the first time (01:45, first pass)", True, "2026-11-01T05:45:00Z", days=["sun"], run_time="01:30", grace_minutes=120),
        window_case("dst-repeated-time-runs-once", "and a run made in the first pass covers the second (01:40, second pass)", False, "2026-11-01T06:40:00Z", last_run="2026-11-01T05:35:00Z",
                    days=["sun"], run_time="01:30", grace_minutes=120),
    ]


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
    cases.extend(window_cases())
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
