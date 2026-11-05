"""The interface of Proactive: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("proactivity", kind="event", entry="due", example={"schedules": [], "now": "2026-07-12T09:00:00Z"})
@runtime_checkable
class Proactive(typing.Protocol):
    """Lets the system act without being asked: given its standing schedules and the time, returns the triggers that are due (each a mapping
    with ``schedule``, ``kind`` (requested, event, period, window or elapsed), ``reason`` and the ``request`` to run), by calendar period in the schedule's own zone, on the days and at the time of day of its ``window`` (days, run_time, time_zone, grace_minutes),
    by a requested run or by an event. Given a Prioritization answer as ``priorities`` it returns the triggers in that order, each with its ``rank``,
    ``priority_reason`` and ``metric``, and leaves out what Prioritization holds back, so the entry carries what is due and what matters first."""

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "", priorities: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]: ...
