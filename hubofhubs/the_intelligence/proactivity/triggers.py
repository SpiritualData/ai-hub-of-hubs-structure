"""Proactivity arms: given the system's standing schedules and the time, which of them are due, as triggers the Planner can plan. A trigger names
the schedule, why it fired and the request to run. Modelled on the cadence and request gates of a production autopilot, written here
without any consumer: a schedule is a mapping with ``name``, ``request``, ``cadence`` (daily, weekly or monthly), ``zone`` (an IANA zone
name), ``last_run`` and ``run_requested_at`` (ISO times), and ``events`` (the times of things that happened since).

``calendar_and_events`` compares **calendar periods** in the schedule's own zone (a daily schedule is due when it has not run yet today
there, not when 24 hours passed, and an evening run does not make the next morning look done), treats a run requested after the last run as
due, and treats an event after the last run as due when the schedule is reactive. An unreadable time fails open to due (a corrupt stamp
never wedges a schedule); an unknown zone falls to the machine's own zone, never to UTC. ``elapsed_hours`` is the naive reading, due when
the cadence's hours have passed, kept as the bound that loses days.

Every trigger says what kind it is (``KINDS``: ``requested``, ``event``, ``period`` or ``elapsed``), so a consumer can tell a person's request from the clock.
A schedule that names an ``event_source`` is reactive, and ``attach_events`` turns the items a consumer pulled from Body's Intake Sources (each a mapping with
``source`` and ``at``) into the events of the schedules that name that source, so a consumer's own event source is declared there and never in hub code.
The arms also take a Prioritization answer (``priorities``): the due triggers then come back in its order, each with its ``rank``, ``priority_reason`` and ``metric``,
and the work it holds back is left out (``in_priority_order``). Standard library plus the hub and ``esoi``."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from esoi import implementation

HOURS = {"daily": 24, "weekly": 24 * 7, "monthly": 24 * 30}
KINDS = ("requested", "event", "period", "elapsed")
#: The fields of a schedule that Prioritization reads when it puts due work in order (see ``hubofhubs.the_consciousness.prioritization.types.FIELDS``).
PRIORITY_FIELDS = ("rank", "deadline", "asked_at", "blocked_by", "waiting", "last_nudged_at")


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


def trigger(schedule: Mapping[str, Any], why: str, kind: str) -> Dict[str, Any]:
    return {"schedule": str(schedule.get("name", "")), "kind": kind, "reason": why, "request": str(schedule.get("request", ""))}


def attach_events(schedules: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]] = ()) -> List[Dict[str, Any]]:
    """The schedules with the pulled ``events`` added: each event (``source`` and ``at``) joins the ``events`` of every schedule whose ``event_source`` is that
    source, and a schedule with an ``event_source`` is reactive. An event with no readable ``at`` is left out, as an unreadable event time is everywhere."""
    out = []
    for schedule in schedules:
        copy = dict(schedule)
        source = str(copy.get("event_source") or "")
        if source:
            copy["reactive"] = True
            copy["events"] = list(copy.get("events") or ()) + [e.get("at") for e in events if str(e.get("source") or "") == source and parse(e.get("at"))]
        out.append(copy)
    return out


def candidate_of(due: Mapping[str, Any], schedules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """A due trigger as a Prioritization candidate: the schedule's name as id, its own ``kind`` or ``standing-work``, and the priority fields it carries."""
    schedule = next((s for s in schedules if str(s.get("name", "")) == due["schedule"]), {})
    found = {"id": due["schedule"], "kind": str(schedule.get("kind") or "standing-work"), "title": str(schedule.get("title") or due["schedule"]),
             "request": due["request"]}
    found.update({f: schedule[f] for f in PRIORITY_FIELDS if f in schedule})
    return found


def in_priority_order(triggers: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]], priorities: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """The due triggers and the other waiting ``candidates`` in the order of a Prioritization answer, each with ``rank``, ``priority_reason`` and ``metric``. A
    candidate that is not a schedule comes back as a trigger of kind ``waiting``. What Prioritization holds back is left out; a due trigger it did not mention
    follows the rest in the order given. With no answer the triggers come back as they were."""
    if not priorities or "ordered" not in priorities:
        return [dict(t) for t in triggers]
    by_id = {t["schedule"]: dict(t) for t in triggers}
    others = {str(c.get("id")): c for c in candidates}
    held = {str(h.get("id")) for h in priorities.get("held") or ()}
    out: List[Dict[str, Any]] = []
    for item in priorities["ordered"]:
        ident = str(item["id"])
        base = by_id.pop(ident, None)
        if base is None:
            other = others.get(ident, {})
            base = {"schedule": ident, "kind": "waiting", "reason": "waiting work that is not a schedule", "request": str(other.get("request") or item.get("request") or "")}
        out.append(dict(base, rank=item["rank"], priority_reason=item["reason"], metric=item["metric"]))
    out.extend(t for ident, t in by_id.items() if ident not in held)
    return out


@implementation("proactivity", "calendar_and_events")
class CalendarAndEvents:
    """Due by calendar period in the schedule's zone, by a later run request, or by a later event for a reactive schedule."""
    REQUIRES = ()     # standard library

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "", priorities: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        return in_priority_order(self.triggers(schedules, now), (), priorities)

    def triggers(self, schedules: Sequence[Mapping[str, Any]], now: str) -> List[Dict[str, Any]]:
        moment = parse(now) or datetime.now(timezone.utc)
        out: List[Dict[str, Any]] = []
        for schedule in schedules:
            last = parse(schedule.get("last_run"))
            asked = parse(schedule.get("run_requested_at"))
            if asked is not None and (last is None or asked > last):
                out.append(trigger(schedule, "a run was requested after the last run", "requested"))
                continue
            if schedule.get("reactive"):
                events = [e for e in (parse(x) for x in schedule.get("events") or ()) if e is not None]
                if (last is None and events) or any(last is not None and e > last for e in events):
                    out.append(trigger(schedule, "something happened since the last run", "event"))
                continue
            if last is None or self.new_period(schedule, last, moment):
                out.append(trigger(schedule, "the schedule has not run in this period", "period"))
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


@implementation("proactivity", "elapsed_hours")
class ElapsedHours:
    """Due when the cadence's hours have passed since the last run: the reading that lets one late run skip the next morning's."""
    REQUIRES = ()     # standard library

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "", priorities: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        return in_priority_order(self.triggers(schedules, now), (), priorities)

    def triggers(self, schedules: Sequence[Mapping[str, Any]], now: str) -> List[Dict[str, Any]]:
        moment = parse(now) or datetime.now(timezone.utc)
        out = []
        for schedule in schedules:
            last = parse(schedule.get("last_run"))
            hours = HOURS.get(str(schedule.get("cadence") or "weekly").lower(), HOURS["weekly"])
            if last is None or moment - last >= timedelta(hours=hours):
                out.append(trigger(schedule, "the cadence's hours have passed", "elapsed"))
        return out
