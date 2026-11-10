"""The interface of Frontend Interface: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("frontend-interface", kind="event", entry="snapshot", example={"events": [{"type": "run-started", "goal": "improve the plan"}], "controls": []})
@runtime_checkable
class FrontendInterfacing(typing.Protocol):
    """Gives a separate frontend (a web page, a mobile app) the AI session as plain data. ``snapshot`` folds the session's events (objects or their dict form)
    and the controls the person sent into one JSON-ready picture: status, goal, what the work serves, steps, helpers with their parent and solution, cost,
    files changed, messages sent and whether each was taken up, the open question, the outcome and what was blocked. ``encode_event``, ``decode_event``,
    ``encode_control`` and ``decode_control`` carry one event or control across the wire and back. Nothing in the data is specific to a terminal.
    Reads nothing and writes nothing."""

    def snapshot(self, events: Sequence[Any], controls: Sequence[Any] = (), structure: Any = None) -> Mapping[str, Any]: ...
    def encode_event(self, event: Any) -> Mapping[str, Any]: ...
    def decode_event(self, data: Mapping[str, Any]) -> Any: ...
    def encode_control(self, control: Any) -> Mapping[str, Any]: ...
    def decode_control(self, data: Mapping[str, Any]) -> Any: ...
