"""The interface of CardStore: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Optional, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_body.internal_context.card_store.card import Card


@solution("card-store", kind="store", entry="search", example="rust release")
@runtime_checkable
class CardStore(typing.Protocol):
    """Keeps cards and finds them again."""

    def add(self, card: Card) -> str: ...
    def get(self, card_id: str) -> Optional[Card]: ...
    def search(self, query: str = "", limit: int = 10, tag: str = "") -> Sequence[Card]: ...
    def delete(self, card_id: str) -> bool: ...
    def count(self) -> int: ...
