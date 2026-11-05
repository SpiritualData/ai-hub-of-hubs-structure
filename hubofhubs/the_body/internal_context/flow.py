"""The composition arm of Internal Context: the system's own context, read through the tool its declaration names, kept as cards, with the
run records of the flow kept apart in the run store."""
from typing import Any, Dict, Mapping, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from hubofhubs.the_body.internal_context.card_store.card import Card
from hubofhubs.the_body.internal_context.card_store.interface import CardStore
from hubofhubs.the_body.internal_context.run_store.runs import RunStore
from hubofhubs.the_world.tools.file_reading.interface import FileReading

TEXT_SUFFIXES = (".md", ".csv", ".txt")


@implementation("internal-context", "composition")
class InternalContextComposition:
    """The system's own context. The default declaration is local files at ``root`` (a folder that belongs to the system, read by File Reading)
    plus the configuration the tools need; a system replaces it by declaring its own sources, whose data belongs to the system or to a person,
    and the tool that reads them. What the Subconscious reads comes only through here: ``read`` returns the cards that match, ``corpus`` returns
    every readable item (the kept cards and the text files of the declared folder) as text by id, and ``keep`` adds cards. The run record goes to
    the run store, never into the cards, so recall never returns a past run as knowledge."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, store: CardStore, reader: Lazy[FileReading], root: str = "", runs_folder: str = ""):
        self.store, self.reader, self.root = store, reader, root
        self.runs = RunStore(runs_folder)

    def declared(self) -> Sequence[Mapping[str, Any]]:
        where = self.root or "no folder declared"
        return [{"kind": "local files", "where": where, "tool": "read-files", "belongs_to": "system", "default": True},
                {"kind": "tool configuration", "where": "the environment of the process and the secrets it names", "tool": "", "belongs_to": "system", "default": True}]

    def read(self, query: str, limit: int = 5) -> Sequence[Card]:
        return list(self.store.search(query, limit=limit))

    def corpus(self) -> Mapping[str, str]:
        found: Dict[str, str] = {card.id: card.text for card in self.store.search("", limit=max(self.store.count(), 1))}
        if self.root:
            names = self.reader.list(self.root, TEXT_SUFFIXES)
            found.update(self.reader.read(self.root, names))
        return found

    def keep(self, cards: Sequence[Card]) -> int:
        for card in cards:
            self.store.add(card)
        return len(cards)

    def record(self, run: Mapping[str, Any]) -> str:
        return self.runs.add(run)

    def runs_so_far(self, limit: int = 10) -> Sequence[Mapping[str, Any]]:
        return self.runs.latest(limit)
