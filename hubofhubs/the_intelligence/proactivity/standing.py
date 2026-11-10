"""The hub's default timing for the structure watch outside any consumer schedule (``ahohs work`` and the interactive terminal), decided with Proactivity's own triggers.

The watch is a reactive standing schedule: structure or work changing is its event, and Proactivity says it is due when an event came after the last watch (``calendar_and_events``).
Two moments ask it: the END of a work run that changed files or records (so it shapes the next planned work), and the START of a session when the last watch is older than a day and
something changed. A digest the last watch already saw is never watched again (the watch itself makes no call then), a setting turns it off, and the call is refused once the run is at
the soft share of its ceilings. Standard library plus the hub."""
from datetime import timedelta
from typing import Any, Dict, Mapping, Optional

from hubofhubs.the_intelligence.proactivity.triggers import CalendarAndEvents, parse

STALE_AFTER = timedelta(hours=24)
SCHEDULE = "structure-watch"
END_OF_RUN, START_OF_SESSION = "end_of_run", "session_start"


def schedule_of(last_watch: Optional[str], changed_at: Optional[str]) -> Dict[str, Any]:
    """The standing schedule: reactive, with the time things changed as its event, and the last watch as its last run."""
    return {"name": SCHEDULE, "request": "watch the structure", "reactive": True, "last_run": last_watch or "", "events": [changed_at] if changed_at else []}


def due(moment: str, now: str, last_watch: Optional[str] = None, changed_at: Optional[str] = None, off: bool = False) -> Mapping[str, Any]:
    """``{"due": bool, "reason": str}`` for ``moment`` (``END_OF_RUN`` or ``START_OF_SESSION``). ``changed_at`` is when the run or the records last changed, empty when nothing did."""
    if off:
        return {"due": False, "reason": "the setting is off"}
    triggers = CalendarAndEvents().due([schedule_of(last_watch, changed_at)], now)
    if not triggers:
        return {"due": False, "reason": "nothing changed since the last watch"}
    if moment == START_OF_SESSION:
        last, here = parse(last_watch), parse(now)
        if last is not None and here is not None and here - last < STALE_AFTER:
            return {"due": False, "reason": "the last watch is less than a day old"}
    return {"due": True, "reason": "something changed since the last watch" + (" and the last watch is older than a day" if moment == START_OF_SESSION else "")}
