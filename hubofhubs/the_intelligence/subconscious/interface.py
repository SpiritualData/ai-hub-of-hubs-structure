"""The interface of Remembering: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_body.internal_context.card_store.card import Card


@solution("the-subconscious", kind="event", entry="recall", example="rust release")
@runtime_checkable
class Remembering(typing.Protocol):
    """Recalls what is known about a query: the area every memory arm competes in, whether it is built from the hub's parts
    (a card store searched directly) or is one product that stores, builds and recalls on its own."""

    def recall(self, query: str, limit: int = 5) -> Sequence[Card]: ...
    def prepare(self, request: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000) -> Mapping[str, Any]: ...
