"""InternalContextComposition."""
import json
import time
from typing import Any, Mapping, Sequence
from esoi import implementation
from esoi.assemble import Lazy
from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_intelligence.subconscious.cards_from_files.interface import CardsFromFiles
from hubofhubs.the_body.internal_context.card_store.interface import CardStore


@implementation("internal-context", "composition")
class InternalContextComposition:
    """The system's own context as cards: read from the Card Store, and built from files by Cards From Files. The default declaration is local
    files at a standard location that belongs to the system, plus the configuration the tools need; a system replaces it by declaring its own
    sources, whose data belongs to the system or to a person, and the tool that reads them. The run record is kept as a card of the store."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, store: CardStore, builder: Lazy[CardsFromFiles]):
        self.store, self.builder = store, builder

    def declared(self) -> Sequence[Mapping[str, Any]]:
        return [{"kind": "local files", "where": "the standard folder of the system", "tool": "file-editing", "belongs_to": "system", "default": True},
                {"kind": "tool configuration", "where": "the environment of the process and the secrets it names", "tool": "", "belongs_to": "system", "default": True}]

    def read(self, query: str, limit: int = 5) -> Sequence[Card]:
        return list(self.store.search(query, limit=limit))

    def record(self, run: Mapping[str, Any]) -> str:
        identifier = f"run-{run.get('id') or int(time.time() * 1000)}"
        self.store.add(Card(identifier, json.dumps(run, default=str, sort_keys=True), source="run record", tags=("run-record",)))
        return identifier
