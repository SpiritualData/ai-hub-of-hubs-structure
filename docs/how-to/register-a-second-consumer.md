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
- Only the entry functions (`assemble`, `run`, `stream`, `needs`) read the process environment, and only when you give no `environ`. Settings (`options`, `selections`, `selection_environ`) are fields of `AssemblyConfig`.

## The one line

```python
import hubofhubs
result = hubofhubs.run("what is the latest Rust release?")   # one input in, one Result out; the best-measured arm of every part
system = hubofhubs.assemble()                                 # every seat with a selected arm; system.pending says what the rest need
system = hubofhubs.assemble(arms={"call-a-model": "anthropic"}, options={"card-store": {"path": "cards.db"}}, lock="esoi.lock.json")   # only what differs
```

`run(input, seat=None, on_event=None, **overrides)` is the single entry point (the `ahohs run` command wraps it): `seat` is `"ask"` (default),
`"search"`, `"papers"` or `"recall"`; `on_event` receives the hub's typed events live; `Result.events` keeps them. `stream(...)` is the same
call as a generator. `needs(seat)` lists what the selected arms still need; `run` raises `Needs` with those lines when a key is missing.

`assemble()` builds each seat whose selected arm needs nothing more from you. Today that is `call-a-model`, `card-store`, `choose-a-model-tier`, `model-call`,
`read-registry-freshness`, `score-hub-connections` and `watch-for-risk`; the other seats are in `system.pending`, one line each saying what to pass:
`arms={seat: <arm>}` where no arm is selected yet (several arms await the measurement of their seat), `options={seat: {argument: ...}}`,
`provided={seat: <your object>}`, or the variable to set (`set ANTHROPIC_API_KEY (option 'api_key')`).

`environ` defaults to your process environment; pass a mapping to replace it (tests, sandboxes). An arm declares as data which of its options come from
which variable (`ENVIRON = {"api_key": "ANTHROPIC_API_KEY"}` on the arm), `options` always win over it, and the reason line names
the variables used, never their values. `model-call` has the arm `via_call_a_model`, selected by its metric: it asks whichever
`call-a-model` arm you choose, so `arms={"call-a-model": "anthropic"}` plus `ANTHROPIC_API_KEY` in `environ` gives both.

`call-a-model` defaults to `claude_cli`: it runs `claude -p` (Claude Code) on your subscription login, with no API key, and needs only
the `claude` executable on PATH. Every other vendor stays selectable with one argument: `hubofhubs.assemble(arms={"call-a-model": "gemini"})`
(or `anthropic`, `openai`, `deepseek`), and `arms={"call-a-model": "multi_provider"}` with `options={"call-a-model": {"primary": ...}}` routes
among several. A consumer's own default (a `Binding` selection) sits between the hub's and a per-call `arms=`.
