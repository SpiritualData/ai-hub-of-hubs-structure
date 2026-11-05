"""The interface of LongTermMemory: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("long-term-memory", kind="event", entry="recall", example={"query": "rust release", "person": ""})
@runtime_checkable
class LongTermMemory(typing.Protocol):
    """Retains what happened across requests under a retention policy and recalls it over the Body's store."""

    def recall(self, query: str, person: str = "", limit: int = 5) -> Sequence[Mapping[str, Any]]: ...
    def retain(self, item: Mapping[str, Any], person: str = "") -> str: ...
