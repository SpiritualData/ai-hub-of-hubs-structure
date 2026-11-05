"""The interface of Planning: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("planner", kind="event", entry="plan", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class Planning(typing.Protocol):
    """Breaks a request into pieces (a list of mappings with ``piece``, ``sub_goal`` and ``tool``, the worker category that fits it or empty).
    On a replan, ``unmet`` carries the failed pieces and why, and a piece that already met its sub-goal is not planned again."""

    def plan(self, request: str, context: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
             guidance: Optional[Mapping[str, Any]] = None, unmet: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]: ...
