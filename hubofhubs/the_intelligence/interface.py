"""The interface of InformationProcessing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("the-intelligence", kind="event", entry="process", example={"request": "what is the latest Rust version?", "person": ""})
@runtime_checkable
class InformationProcessing(typing.Protocol):
    """Processes one request: the long view is read, the request becomes a target with a budget, the Mind plans, delegates and writes, and the
    goal and the response quality are checked. When the goal is unmet the flow returns to the Planner within the budget; when the budget or the
    authority runs out it goes to Judgment Calls. Returns a mapping with ``answer``, ``attempts``, ``escalation`` (Judgment Calls' decision, when
    the flow stopped unmet) and ``steps``. ``proactive`` returns the triggers Proactivity says are due together with the
    other waiting work, most important first as Prioritization orders it for the person (each with its ``rank``, ``priority_reason`` and ``metric``)."""

    def process(self, request: str, person: str = "", representative: Optional[Mapping[str, Any]] = None,
                priorities: Optional[Mapping[str, Any]] = None, cancelled: Optional[Callable[[], bool]] = None) -> Mapping[str, Any]: ...
    def proactive(self, schedules: Sequence[Mapping[str, Any]], now: str = "", person: str = "", candidates: Sequence[Mapping[str, Any]] = (),
                  stated: Optional[Mapping[str, Any]] = None, events: Sequence[Mapping[str, Any]] = ()) -> Sequence[Mapping[str, Any]]: ...
