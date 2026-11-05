"""The interface of InternalContexting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_body.internal_context.card_store.card import Card


@solution("internal-context", kind="event", entry="read", example="rust release")
@runtime_checkable
class InternalContexting(typing.Protocol):
    """Reads a system's own context through the tool its declaration names (local files at a standard location by default) and returns it as
    cards; ``declared`` lists the sources the system declared, each with ``belongs_to`` (the system or a person) and the configuration, environment
    variables, secrets and stored authentication its tool needs; ``record`` keeps the run record the flow wrote, which Integrity audits."""

    def read(self, query: str, limit: int = 5) -> Sequence[Card]: ...
    def declared(self) -> Sequence[Mapping[str, Any]]: ...
    def record(self, run: Mapping[str, Any]) -> str: ...
