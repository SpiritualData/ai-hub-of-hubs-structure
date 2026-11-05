"""The interface of InternalContexting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_body.internal_context.card_store.card import Card


@solution("internal-context", kind="event", entry="read", example="rust release")
@runtime_checkable
class InternalContexting(typing.Protocol):
    """The system's own context, the only way the Subconscious reads it. ``read`` returns the cards that match a query; ``corpus`` returns every
    readable item (kept cards and the text files of the declared sources) as text by id, for the Context Retriever to pick from; ``keep`` adds
    cards; ``declared`` lists the sources the system declared, each with ``belongs_to`` (the system or a person) and the configuration, environment
    variables, secrets and stored authentication its tool needs; ``record`` keeps the run record the flow wrote in the run store (never in the
    cards), which Integrity audits, and ``runs_so_far`` lists the newest records."""

    def read(self, query: str, limit: int = 5) -> Sequence[Card]: ...
    def corpus(self) -> Mapping[str, str]: ...
    def keep(self, cards: Sequence[Card]) -> int: ...
    def declared(self) -> Sequence[Mapping[str, Any]]: ...
    def record(self, run: Mapping[str, Any]) -> str: ...
    def runs_so_far(self, limit: int = 10) -> Sequence[Mapping[str, Any]]: ...
