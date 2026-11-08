"""The interface of CriticalThinking: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("critical-thinking", kind="event", entry="evaluate", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class CriticalThinking(typing.Protocol):
    """Critical Thinking: ``translate`` turns a request into a target, ``pursue`` keeps working on an unmet goal with the untried reads within a budget, ``evaluate`` checks the goal and judges the response against the
    quality profile resolved from the Representative, Guidance and Prioritization (the default profile when none is given), ``check_decision`` has small independent checks check a draft decision
    (a pick among options or a reply) within a call cap, ``upkeep`` keeps a milestone's metrics able to show progress and ``progress`` makes one measured AI increment on a milestone
    (upkeep, the increment rule, before, the work, ``pursue`` refusing bookkeeping alone, after)."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
    def evaluate(self, request: str, response: str = "", target: Optional[Mapping[str, Any]] = None, evidence: str = "",
                 representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                 priorities: Optional[Mapping[str, Any]] = None, outcome: Optional[Any] = None) -> Mapping[str, Any]: ...
    def check_decision(self, draft: Any, binding: Any, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]: ...
    def pursue(self, goal: str, done_standard: str, draft: Any, attempt: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
               means: Sequence[Mapping[str, Any]] = (), budget: Optional[Mapping[str, Any]] = None,
               announce: Optional[Callable[[str], Any]] = None, check: Optional[Callable[[Any], Mapping[str, Any]]] = None,
               progress: bool = False) -> Mapping[str, Any]: ...
    def upkeep(self, spec: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], readers: Optional[Mapping[str, Any]] = None, today: str = "",
               ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]: ...
    def progress(self, milestone: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], work_items: Sequence[Mapping[str, Any]],
                 work: Callable[[Mapping[str, Any]], Mapping[str, Any]], judge: Optional[Callable[[Optional[str], str], Any]] = None,
                 means: Sequence[Mapping[str, Any]] = (), readers: Optional[Mapping[str, Any]] = None, today: str = "",
                 ask: Optional[Callable[[str], str]] = None, kept: Any = None) -> Mapping[str, Any]: ...
