"""The interface of Guiding: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("guidance", kind="event", entry="nudge", example={"request": "what is the latest Rust release?", "objectives": []})
@runtime_checkable
class Guiding(typing.Protocol):
    """An infrequent longer-term nudge for the Planner, with the context-specific quality criteria; ``None`` when none is due."""

    def nudge(self, request: str, objectives: Sequence[Mapping[str, Any]] = ()) -> Optional[Mapping[str, Any]]: ...
