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
    (upkeep, the increment rule, before, the work, ``pursue`` refusing bookkeeping alone, after). ``consider`` gives each solution a request concerns its own
    pass (Solution Passes), ``check_pieces`` holds each plan piece to its own solution's target and says whether the pieces still combine, and
    ``write_back`` has ESOI Application record what the passes and checks taught, ``build_out`` gives a piece that falls short of its metric depth (split by its missing requirements, each part with its own sub-prompt, recombined and checked again); ``translate`` given ``solutions`` holds the goal to their own targets."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None, solutions: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]: ...
    def consider(self, request: str, briefs: Mapping[str, Any], own_passes: Optional[Mapping[str, Callable[..., Mapping[str, Any]]]] = None,
                 limits: Optional[Mapping[str, int]] = None, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]: ...
    def build_out(self, item: Mapping[str, Any], work: Callable[[Mapping[str, Any]], str], check: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
                  split: Optional[Callable[..., Sequence[Mapping[str, Any]]]] = None, combine: Optional[Callable[..., str]] = None,
                  budget: Optional[Mapping[str, int]] = None, base: Optional[str] = None) -> Mapping[str, Any]: ...
    def check_pieces(self, results: Sequence[Mapping[str, Any]], considered: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def write_back(self, considered: Mapping[str, Any], checked: Optional[Mapping[str, Any]] = None, today: str = "",
                   apply: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None) -> Mapping[str, Any]: ...
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
