"""The composition arm of ``the-subconscious``: recall is the cards the Context Retriever picks from the store's cards for the query, then the cards of
the selected store that match it; ``prepare`` is what the Subconscious hands the Mind: those cards, what Intuition offers unasked and, given a
folder's files, the pieces the Context Retriever picks within a token budget; ``learn`` fills the store from a folder's files through the selected card builder, which is built
on first use, so recall alone never asks for what building cards needs (a model)."""
from typing import Any, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_intelligence.subconscious.cards_from_files.interface import CardsFromFiles
from hubofhubs.the_body.internal_context.card_store.interface import CardStore
from hubofhubs.the_intelligence.subconscious.context_retriever.interface import ContextRetrieval
from hubofhubs.the_intelligence.subconscious.intuition.interface import Intuiting
from hubofhubs.the_self.steps import listing, skipped, take


@implementation("the-subconscious", "card_recall")
class CardRecall:
    """Recall built from the hub's parts: the cards the selected Context Retriever picks from the store's cards for the query come first, then
    the cards the selected store finds by the query's words, each card once."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, store: CardStore, builder: Lazy[CardsFromFiles], intuition: Lazy[Intuiting], retriever: Lazy[ContextRetrieval]):
        self.store = store
        self.builder = builder
        self.intuition = intuition
        self.retriever = retriever

    def prepare(self, request: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000) -> Mapping[str, Any]:
        """What the Mind is handed for a request: the recalled cards, what Intuition offers (no arm yet, so a pending step), and the pieces of
        ``files`` the Context Retriever picks when files are given. Every step is reported, none is made up."""
        offered = take(self.intuition, "the-intuition", request=request)
        pieces = take(self.retriever, "context-retriever", query=request, files=files, budget_tokens=budget_tokens) if files else skipped(
            "context-retriever", "no files were given")
        return {"cards": list(self.recall(request)), "offered": offered.output or [], "pieces": list(pieces.output or []),
                "steps": listing([offered, pieces])}

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
        cards = list(self.store.search("", limit=max(self.store.count(), 1)))
        by_id = {card.id: card for card in cards}
        for hit in (self.retriever.retrieve(query, {card.id: card.text for card in cards}) if cards else ()):
            card = by_id.get(hit.file)
            if card is not None and card.id not in [c.id for c in found]:
                found.append(card)
        for card in self.store.search(query, limit=limit):
            if card.id not in [c.id for c in found]:
                found.append(card)
        return found[:limit]
