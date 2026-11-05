"""The interface of IntakeSourcing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("intake-sources", kind="event", entry="pull", example={"source": "", "limit": 10})
@runtime_checkable
class IntakeSourcing(typing.Protocol):
    """Body's intake adapters: ``sources`` lists where this system's requests come from (a chat, a task queue, a place meeting action items are
    written; a system declares its own), and ``pull`` takes the requests waiting at one of them (each a mapping with ``text``, ``person`` and
    ``source``, and an ``at`` time when it is an event that Proactivity should count), handing each over once."""

    def sources(self) -> Sequence[Mapping[str, Any]]: ...
    def pull(self, source: str = "", limit: int = 10) -> Sequence[Mapping[str, Any]]: ...
