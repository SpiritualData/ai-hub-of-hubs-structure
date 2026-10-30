# Quickstart: a second consumer in a few lines

A consumer with no Quest content registers a part it owns, assembles, and reads why each part was chosen. This file is run
as `tests/test_quickstart.py`: if it stops working, a test fails.

```python
import hubofhubs
from hubofhubs.card import Card


class ListCardStore:                     # a part the consumer owns; it satisfies hubofhubs.seats.CardStore
    def __init__(self):
        self.cards = {}

    def add(self, card):
        self.cards[card.id] = card
        return card.id

    def get(self, card_id):
        return self.cards.get(card_id)

    def search(self, query="", limit=10, tag=""):
        words = query.lower().split()
        found = [c for c in self.cards.values() if all(w in c.text.lower() for w in words)]
        return found[:limit]

    def delete(self, card_id):
        return self.cards.pop(card_id, None) is not None

    def count(self):
        return len(self.cards)


hubofhubs.register("card-store", "my-list-store", ListCardStore)     # a name the consumer owns
config = hubofhubs.AssemblyConfig(solutions=("card-store",), selections={"card-store": "my-list-store"})
system = hubofhubs.assemble(config)                                   # built once, at startup, then frozen

system["card-store"].add(Card("a", "hello from a second consumer"))
print(system["card-store"].search("second"))
print(system.reasons[0])

default = hubofhubs.assemble(hubofhubs.AssemblyConfig(solutions=("card-store",)))   # no selection: the hub's own default arm
print(default.reasons[0])
```

What to know:

- A seat is a Protocol in `hubofhubs.seats`; an arm's constructor parameters typed with a seat are its needs, and
  `assemble` builds them first. A cycle or an unmet need stops startup and names the chain.
- `provided={"model-call": my_model}` hands the hub an object you already have; it wins for that seat. `model-call` is an external seat: you always provide it. `search-backend` is external too, but the hub ships arms for it
  (`searxng`, `serper`, `brave`, `tavily`, `gemini`, `provider`; extras `web`, `gemini`); none is selected by default, so name one or provide your own.
- A name is lower-case letters, digits, `_` and `-`. A value with `:` or `.` is refused before anything is imported.
- The hub reads no environment. Settings (`options`, `selections`, `selection_environ`) are fields of `AssemblyConfig`.
