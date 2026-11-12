"""The interface of LongTermMemory: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("long-term-memory", kind="event", entry="recall", example={"query": "rust release", "person": ""})
@runtime_checkable
class LongTermMemory(typing.Protocol):
    """Retains what happened across requests under a retention policy and recalls it over the Body's store. An item is a mapping with ``text``,
    optionally ``id``, ``at`` (an ISO time; the time of retaining when absent), ``scope_tags`` and ``affinity_tags``. ``person`` is the subject: a person or an AI representative. ``recall`` returns at most ``limit`` of the person's retained items that
    bear on the query (``id``, ``text``, ``at``), most relevant first with the newer ahead on a tie, at the time ``now`` (the clock when empty); an item
    older than the retention period is gone, and one subject's items are never returned for another, and a tagged item is returned only when its ``scope_tags`` share one with the turn's ``scope_tags``, what the asker may open (a turn with none sees no tagged item); ``affinity_tags`` only rank the turn's own scope first and hide nothing."""

    def recall(self, query: str, person: str = "", limit: int = 5, now: str = "", scope_tags: Sequence[str] = (), affinity_tags: Sequence[str] = ()) -> Sequence[Mapping[str, Any]]: ...
    def retain(self, item: Mapping[str, Any], person: str = "") -> str: ...
