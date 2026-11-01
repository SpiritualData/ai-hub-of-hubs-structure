# Assemble the hub and run your first seat in five minutes

By the end you will have assembled the hub, seen which seats it built and which it asks you to finish, and used the first seat
(`card-store`) to keep and find a card. This page is run by `tests/test_tutorial.py`: if it stops working, a test fails.

You need Python 3.11 or later and the `esoi` library on your path (the hub's only dependency).

## 1. Install the package

From a checkout of this repository:

```bash
pip install -e .
```

The core needs nothing else. An arm that uses a third-party library has an extra named in `pyproject.toml` (`web`, `gemini`,
`anthropic`, `openai`, `qdrant`, `bm25` and others); [requirements by arm](../reference/requirements-by-arm.md) lists which arm
needs which.

## 2. Assemble

```python
import hubofhubs
from hubofhubs.card import Card

system = hubofhubs.assemble()
print(sorted(system.pending))
```

`assemble()` builds every seat whose selected arm needs nothing more from you and leaves the others in `system.pending`, one
line each saying what to pass. The hub reads no environment itself: to use your keys, hand the mapping over with
`hubofhubs.assemble(environ=os.environ)`. The seats printed are the ones still waiting for you, for example `search-backend` (a key such as `GEMINI_API_KEY`) and `act-in-the-world` (no arm is selected yet). `call-a-model` is already built: its default arm is `claude_cli`, which runs `claude -p` on your Claude Code subscription and needs no key.

## 3. Use the first seat

```python
store = system["card-store"]
store.add(Card(id="first", text="The hub keeps one arm per seat", tags=("note",)))
print(store.search("one arm"))
print(store.count())
```

`card-store` is built on the standard library (SQLite in memory by default). `search` matches every word of the query as a
case-insensitive substring of a card's text, and adding the same id again replaces the card. Pass
`options={"card-store": {"path": "cards.db"}}` to `assemble` to keep the cards in a file.

## 4. See why each part was chosen

```python
print(system.reasons[0])
```

Each line names the seat, the arm, the layer that chose it and the package version. Nothing is chosen by preference: the
selected arm of a seat is set from its measured results (see [how we measure](../explanation/how-we-measure.md)).

## 5. Finish a pending seat

Read the line for the seat you want in `system.pending[seat]`. A missing key is named with the official signup link; a seat with
no selected arm lists the arms to choose from. For a key, set the variable and pass it in `environ`. For a choice, pass
`arms={seat: <arm>}`. To see every variable the default assembly can use, open `.env.example`, which is generated from the arms'
declarations.

## Next

- Register an arm of your own: [register a second consumer](../how-to/register-a-second-consumer.md).
- Install only what a seat needs: [install what your seats need](../how-to/install-what-your-seats-need.md).
- Why an arm holds its seat: [how we measure](../explanation/how-we-measure.md) and the [evidence by arm](../reference/evidence-by-arm.md).
