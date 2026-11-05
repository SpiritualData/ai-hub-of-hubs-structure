"""The interface of HigherMind: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("higher-mind", kind="event", entry="view", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class HigherMind(typing.Protocol):
    """The long view for one request: the objectives it serves (the person's recorded ``objectives``, each a solution milestone), ``priority`` (which of them matter
    most to the person, as Prioritization orders them), what is remembered and the guidance for the Planner, one step each."""

    def view(self, request: str, person: str = "", objectives: Sequence[Mapping[str, Any]] = (), stated: Optional[Mapping[str, Any]] = None,
             now: str = "") -> Mapping[str, Any]: ...
