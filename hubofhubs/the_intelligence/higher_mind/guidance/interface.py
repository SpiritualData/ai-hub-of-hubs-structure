"""The interface of Guiding: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("guidance", kind="event", entry="nudge", example={"request": "what is the latest Rust version?", "objectives": []})
@runtime_checkable
class Guiding(typing.Protocol):
    """An infrequent longer-term nudge for the Planner, with the context-specific quality criteria; ``None`` when none is due.

    An objective is a mapping with ``id``, ``name``, ``next_target`` and optionally ``reading``, ``in_focus``, ``nudged_recently`` and ``criteria``. A nudge is a mapping
    with ``nudge`` (one sentence), ``objective`` (its id) and ``quality_criteria`` (criterion name to weight, as Response Quality's profile layers them)."""

    def nudge(self, request: str, objectives: Sequence[Mapping[str, Any]] = ()) -> Optional[Mapping[str, Any]]: ...
