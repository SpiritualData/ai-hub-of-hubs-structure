"""The interface of RiskWatching: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, runtime_checkable
from esoi import solution


@solution("nervous-system", kind="event", entry="watch", example="delete the old backup folder")
@runtime_checkable
class RiskWatching(typing.Protocol):
    """Watches a run through a cheap digest and sends one signal: a ``RiskSignal`` (severity none, low, medium or high, and the reason). It does
    not route: what to do with a signal belongs to Judgment Calls (ask, proceed or decline for a person) and to the Planner and Delegation
    (answering now, handing work to an agent session, changing course). Never raises. The consumer's prompt is data passed to the arm, not part of
    the hub. ``watch`` reads a digest of one step; ``digest`` builds that digest from the step's fields."""

    def digest(self, **fields: Any) -> str: ...
    def watch(self, digest: str, model: str = "") -> Any: ...
