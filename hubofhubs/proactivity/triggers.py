"""Proactivity arms: given the system's standing schedules and the time, which of them are due, as triggers the Planner can plan. A trigger names
the schedule, why it fired and the request to run. Modelled on the cadence and request gates of a production autopilot, written here
without any consumer: a schedule is a mapping with ``name``, ``request``, ``cadence`` (daily, weekly or monthly), ``zone`` (an IANA zone
name), ``last_run`` and ``run_requested_at`` (ISO times), and ``events`` (the times of things that happened since).

``calendar_and_events`` compares **calendar periods** in the schedule's own zone (a daily schedule is due when it has not run yet today
there, not when 24 hours passed, and an evening run does not make the next morning look done), treats a run requested after the last run as
due, and treats an event after the last run as due when the schedule is reactive. An unreadable time fails open to due (a corrupt stamp
never wedges a schedule); an unknown zone falls to the machine's own zone, never to UTC. ``elapsed_hours`` is the naive reading, due when
the cadence's hours have passed, kept as the bound that loses days. Standard library plus the hub and ``esoi``."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from esoi import implementation

HOURS = {"daily": 24, "weekly": 24 * 7, "monthly": 24 * 30}


def parse(raw: Any) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def local(moment: datetime, zone: str) -> datetime:
    try:
        return moment.astimezone(ZoneInfo(zone)) if zone else moment.astimezone()
    except (ZoneInfoNotFoundError, ValueError):
        return moment.astimezone()      # the machine's own zone, never UTC


def trigger(schedule: Mapping[str, Any], why: str) -> Dict[str, Any]:
    return {"schedule": str(schedule.get("name", "")), "reason": why, "request": str(schedule.get("request", ""))}


@implementation("the-proactivity", "calendar_and_events")
class CalendarAndEvents:
    """Due by calendar period in the schedule's zone, by a later run request, or by a later event for a reactive schedule."""
    REQUIRES = ()     # standard library

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "") -> Sequence[Mapping[str, Any]]:
        moment = parse(now) or datetime.now(timezone.utc)
        out: List[Dict[str, Any]] = []
        for schedule in schedules:
            last = parse(schedule.get("last_run"))
            asked = parse(schedule.get("run_requested_at"))
            if asked is not None and (last is None or asked > last):
                out.append(trigger(schedule, "a run was requested after the last run"))
                continue
            if schedule.get("reactive"):
                events = [e for e in (parse(x) for x in schedule.get("events") or ()) if e is not None]
                if (last is None and events) or any(last is not None and e > last for e in events):
                    out.append(trigger(schedule, "something happened since the last run"))
                continue
            if last is None or self.new_period(schedule, last, moment):
                out.append(trigger(schedule, "the schedule has not run in this period"))
        return out

    def new_period(self, schedule: Mapping[str, Any], last: datetime, now: datetime) -> bool:
        zone = str(schedule.get("zone") or "")
        then, here = local(last, zone), local(now, zone)
        cadence = str(schedule.get("cadence") or "weekly").lower()
        if cadence == "daily":
            return then.date() < here.date()
        if cadence == "monthly":
            return (then.year, then.month) < (here.year, here.month)
        return then.isocalendar()[:2] < here.isocalendar()[:2]


@implementation("the-proactivity", "elapsed_hours")
class ElapsedHours:
    """Due when the cadence's hours have passed since the last run: the reading that lets one late run skip the next morning's."""
    REQUIRES = ()     # standard library

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "") -> Sequence[Mapping[str, Any]]:
        moment = parse(now) or datetime.now(timezone.utc)
        out = []
        for schedule in schedules:
            last = parse(schedule.get("last_run"))
            hours = HOURS.get(str(schedule.get("cadence") or "weekly").lower(), HOURS["weekly"])
            if last is None or moment - last >= timedelta(hours=hours):
                out.append(trigger(schedule, "the cadence's hours have passed"))
        return out
