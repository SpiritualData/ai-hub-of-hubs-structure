"""The composition arm of ``the-subconscious``. It reads the system's context only through Internal Context: ``prepare`` is what the Subconscious hands
the Mind (the cards Internal Context returns for the request, what Intuition offers unasked and the pieces the Context Retriever picks, within a token budget,
from everything Internal Context can read, plus any files the caller adds); ``recall`` is the cards the Context Retriever picks from the kept cards, then the
cards Internal Context finds by the query's words; ``learn`` fills the kept cards from a folder's files through the selected card builder, which is built on
first use, so recall alone never asks for what building cards needs (a model)."""
from typing import Any, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi import Lazy

from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_intelligence.subconscious.cards_from_files.interface import CardsFromFiles
from hubofhubs.the_body.internal_context.interface import InternalContexting
from hubofhubs.the_intelligence.subconscious.context_retriever.interface import ContextRetrieval
from hubofhubs.the_intelligence.subconscious.intuition.interface import Intuiting
from hubofhubs.the_self.steps import listing, skipped, take


@implementation("the-subconscious", "card_recall")
class CardRecall:
    """Recall built from the hub's parts, read through Internal Context: the cards the selected Context Retriever picks from the kept cards come first,
    then the cards Internal Context finds by the query's words, each card once."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, internal: InternalContexting, builder: Lazy[CardsFromFiles], intuition: Lazy[Intuiting], retriever: Lazy[ContextRetrieval]):
        self.internal = internal
        self.builder = builder
        self.intuition = intuition
        self.retriever = retriever

    def prepare(self, request: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000) -> Mapping[str, Any]:
        """What the Mind is handed for a request: the recalled cards, what Intuition offers (a pending step while it has no arm) and the pieces the Context
        Retriever picks from what Internal Context returns and the files given. Every step is reported, none is made up."""
        held = take(self.internal, "internal-context", method="corpus")
        corpus = {**(held.output or {}), **(files or {})}
        offered = take(self.intuition, "the-intuition", request=request)
        pieces = take(self.retriever, "context-retriever", query=request, files=corpus, budget_tokens=budget_tokens) if corpus else skipped(
            "context-retriever", "Internal Context holds nothing to read yet")
        return {"cards": list(self.recall(request)), "offered": offered.output or [], "pieces": list(pieces.output or []),
                "steps": listing([held, offered, pieces])}

    def learn(self, root: str, files: Sequence[str]) -> int:
        """Fill the kept cards from files the consumer already keeps: the selected builder proposes the cards, Internal Context keeps them.
        Returns how many cards were added."""
        proposed = self.builder.build(root, list(files), {})
        return self.internal.keep([Card(id=row["id"], text=row.get("text") or row.get("summary", ""), source=row.get("source", ""),
                                        tags=tuple(row.get("tags") or ())) for row in proposed])

    def recall(self, query: str, limit: int = 5) -> Sequence[Card]:
        found: List[Card] = []
        cards = list(self.internal.read("", limit=10 ** 6))
        by_id = {card.id: card for card in cards}
        for hit in (self.retriever.retrieve(query, {card.id: card.text for card in cards}) if cards else ()):
            card = by_id.get(hit.file)
            if card is not None and card.id not in [c.id for c in found]:
                found.append(card)
        for card in self.internal.read(query, limit=limit):
            if card.id not in [c.id for c in found]:
                found.append(card)
        return found[:limit]
