"""The interface of Reasoning: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("the-mind", kind="event", entry="think", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class Reasoning(typing.Protocol):
    """The Mind: takes in context, plans, delegates and writes for one request. ``authority`` is the Representative's, ``target`` the metric
    the request was translated into, ``guidance`` the Planner's nudge and ``profile`` the resolved quality profile and ``prepared`` what the Subconscious prepared. Returns a mapping with
    ``text``, ``results`` (one per delegated piece), ``pieces`` and ``steps``. On a replan, ``unmet`` is what the last attempt failed and ``outside``
    what its workers brought, which Context Intake takes in. ``considered`` is what each relevant solution's own pass found (with ``prompts`` by
    solution id): each piece is then tied to its solution (``solution_id`` on the piece and its result) and held to that solution's target."""

    def think(self, request: str, authority: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
              guidance: Optional[Mapping[str, Any]] = None, profile: Optional[Any] = None, prepared: Optional[Mapping[str, Any]] = None,
              unmet: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None, budget: Optional[Any] = None,
              cancelled: Optional[Callable[[], bool]] = None, considered: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
