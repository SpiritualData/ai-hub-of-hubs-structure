"""The interface of StructureWatching: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("structure-watch", kind="event", entry="watch", example={"intent": "example", "tables": {}, "runs": [], "now": "2026-11-10T09:00:00Z"})
@runtime_checkable
class StructureWatching(typing.Protocol):
    """Reads a compact digest of the ESOI records of one intent against the recent and planned work and returns at most three items (what needs attention, why now,
    the risk if ignored, a severity and the proposed next step), or none. Makes no call when the digest is the same as the last watch's. Each item is routed through Judgment
    Calls: to a person as a proposal (structure a person wrote, reviewed or owns, what a running experiment holds fixed, anything irreversible) or applied by the AI with
    the change recorded (structure the AI made and nobody reviewed). Never raises."""

    def watch(self, structure: Mapping[str, Any], now: str = "") -> Mapping[str, Any]: ...
