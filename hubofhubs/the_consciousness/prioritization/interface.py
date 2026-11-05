"""The interface of Prioritizing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("prioritization", kind="event", entry="prioritize", example={"person": "", "request": "what is the latest Rust version?"})
@runtime_checkable
class Prioritizing(typing.Protocol):
    """Translates the priorities a person states or implies into ESOI milestones and weights, including quality profile weights."""

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
