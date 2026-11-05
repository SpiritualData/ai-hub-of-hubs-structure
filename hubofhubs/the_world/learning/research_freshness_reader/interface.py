"""The interface of FreshnessReading: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("research-freshness-reader", kind="event", entry="days_since", example="2026-10-01")
@runtime_checkable
class FreshnessReading(typing.Protocol):
    """Reads the registry's recorded dates and reports how old each area's research is."""

    def days_since(self, iso: str, clock: Any = None) -> Optional[int]: ...
    def combine(self, facts: Sequence[Mapping[str, Any]], connections: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...
