"""The interface of Proactive: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("proactivity", kind="event", entry="due", example={"schedules": [], "now": "2026-07-12T09:00:00Z"})
@runtime_checkable
class Proactive(typing.Protocol):
    """Lets the system act without being asked: given its standing schedules and the time, returns the triggers that are due (each a mapping
    with ``schedule``, ``reason`` and the ``request`` to run), by calendar period, by a requested run or by an event."""

    def due(self, schedules: Sequence[Mapping[str, Any]], now: str = "") -> Sequence[Mapping[str, Any]]: ...
