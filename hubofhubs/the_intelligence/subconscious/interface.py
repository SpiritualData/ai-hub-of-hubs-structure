"""The interface of Remembering: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_body.internal_context.card_store.card import Card


@solution("the-subconscious", kind="event", entry="recall", example="rust release")
@runtime_checkable
class Remembering(typing.Protocol):
    """Recalls what is known about a query: the area every memory arm competes in, whether it is built from the hub's parts
    (a card store searched directly) or is one product that stores, builds and recalls on its own. ``prepare`` with the consumer's ESOI ``records`` also
    returns ``solutions``: each solution the request concerns with its generated prompt and the knowledge that bears on it (``knowledge``: retrieved, all or
    none), the scopes above them (``ancestors``) and the solutions relying on them (``dependents``)."""

    def recall(self, query: str, limit: int = 5) -> Sequence[Card]: ...
    def prepare(self, request: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000, records: Any = None,
                knowledge: str = "retrieved", limit: int = 5, depth: int = 3) -> Mapping[str, Any]: ...
