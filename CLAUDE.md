# ai-hub-of-hubs-structure (Python package and distribution `hubofhubs`)

A public repository: the ESOI records and shared structure for assembling the best AI-intelligence hubs, one seat per
part of a mind, chosen by metric and refreshed weekly. Quest AI Runner is its production consumer. This file holds only
what differs from general practice; the `README.md` explains the idea.

## Rules

- **Public hygiene.** No real person names, email addresses, ids, organization-private details or absolute machine paths.
  The organization name SpiritualData and this repo's name are fine.
- **No em dashes** in any text, record or prompt.
- **Records are the source.** `esoi/*.csv` define the intent, problems, ideals, solutions and metrics. Descriptive
  wording belongs to the owner: an AI adds only ids, links, paths and commands, and flags new prose
  "unconfirmed: for Joshua to confirm". Do not invent implementations; a seat with none stays "no arm yet".
- **Selection by metric only.** Set `selected` from the seat's metric result, never from preference.
- **Generic, no consumer content.** The hub holds real executing code (seats as Protocols, arms in extras); its core is the standard library plus `esoi`. No consumer-specific prompts or settings here; those stay in the consumer (QAR for Quest).
- **README seats table** is generated from the registry: run `python3 scripts/status.py`, never edit between its markers by hand.
- **The registry** is `hubofhubs/registry/*.csv`. A capability is a hub connection (a class, counted once), never one service;
  a single service a consumer hand-wires goes in `hub_integrations.csv`. Facts need a dated source; see `docs/refresh.md`.
- **Consumers** hand this package a `Binding`; the package never imports a consumer. Core imports stay stdlib, the package and `esoi` (`tests/test_import_boundary.py`); third-party libraries belong in per-arm extras.
- **No environment reads.** Settings are `HubConfig` fields (`selection_environ` is the only environment `esoi` sees). Names are validated, never import paths. A seat is a `typing.Protocol` declared with `@solution(id)` in `hubofhubs/seats.py`; an arm's constructor parameters typed with a seat are its needs. No alias for a renamed package or arm. Read `docs/resolution-design.md` before changing resolution or assembly.

## Checks

```bash
PYTHONPATH=../evolvable-structure/implementations/python python3 -m esoi check
python3 -m pytest tests/test_registry.py tests/test_status.py tests/test_import_boundary.py   # plus the hub's other small test files
python3 scripts/sync_uses.py --check
```

The ESOI library (`evolvable-structure`) is read-only from here: never edit or commit there.
