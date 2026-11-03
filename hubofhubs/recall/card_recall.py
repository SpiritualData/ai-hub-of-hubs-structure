"""The composition arm of ``remember-and-recall``: recall is the cards the context assembler drew on for the query, then the cards of
the selected store that match it; ``learn`` fills the store from a folder's files through the selected card builder."""
from typing import List, Sequence

from esoi import implementation

from ..card import Card
from ..seats import CardsFromFiles, CardStore, ContextAssembling


@implementation("remember-and-recall", "card_recall")
class CardRecall:
    """Recall built from the hub's parts: the cards the selected context assembler names for the query come first, then the cards the
    selected store finds by the query's words, each card once."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, store: CardStore, assembler: ContextAssembling, builder: CardsFromFiles):
        self.store = store
        self.assembler = assembler
        self.builder = builder

    def learn(self, root: str, files: Sequence[str]) -> int:
        """Fill the store from files the consumer already keeps: the selected builder proposes the cards, the store keeps them.
        Returns how many cards were added."""
        proposed = self.builder.build(root, list(files), {})
        for row in proposed:
            self.store.add(Card(id=row["id"], text=row.get("text") or row.get("summary", ""), source=row.get("source", ""),
                                tags=tuple(row.get("tags") or ())))
        return len(proposed)

    def recall(self, query: str, limit: int = 5) -> Sequence[Card]:
        found: List[Card] = []
        for card_id in self.assembler.assemble(query).card_ids or ():
            card = self.store.get(card_id)
            if card is not None and card.id not in [c.id for c in found]:
                found.append(card)
        for card in self.store.search(query, limit=limit):
            if card.id not in [c.id for c in found]:
                found.append(card)
        return found[:limit]
