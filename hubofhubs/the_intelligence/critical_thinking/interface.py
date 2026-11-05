"""The interface of CriticalThinking: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("critical-thinking", kind="event", entry="evaluate", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class CriticalThinking(typing.Protocol):
    """Critical Thinking: ``translate`` turns a request into a target, ``evaluate`` checks the goal and judges the response against the
    quality profile resolved from the Representative, Guidance and Prioritization (the default profile when none is given)."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
    def evaluate(self, request: str, response: str = "", target: Optional[Mapping[str, Any]] = None, evidence: str = "",
                 representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                 priorities: Optional[Mapping[str, Any]] = None, outcome: Optional[Any] = None) -> Mapping[str, Any]: ...
