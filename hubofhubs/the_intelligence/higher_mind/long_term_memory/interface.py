"""The interface of LongTermMemory: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("long-term-memory", kind="event", entry="recall", example={"query": "rust release", "person": ""})
@runtime_checkable
class LongTermMemory(typing.Protocol):
    """Retains what happened across requests under a retention policy and recalls it over the Body's store. An item is a mapping with ``text``,
    optionally ``id`` and ``at`` (an ISO time; the time of retaining when absent). ``recall`` returns at most ``limit`` of the person's retained items that
    bear on the query (``id``, ``text``, ``at``), most relevant first with the newer ahead on a tie, at the time ``now`` (the clock when empty); an item
    older than the retention period is gone, and one person's items are never returned for another."""

    def recall(self, query: str, person: str = "", limit: int = 5, now: str = "") -> Sequence[Mapping[str, Any]]: ...
    def retain(self, item: Mapping[str, Any], person: str = "") -> str: ...
