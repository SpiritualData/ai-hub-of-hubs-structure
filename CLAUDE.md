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
- **Generated blocks.** The README seats table, evidence table and not-measured list, `docs/reference/registry.md`, `docs/reference/evidence-by-arm.md`, `docs/reference/requirements-by-arm.md`, the headline lines of the two drafts in `drafts/` and `.env.example` are generated: run `python3 scripts/status.py` (also after any new result or arm declaration), then `PYTHONPATH=../evolvable-structure/implementations/python python3 -m esoi requirements --package hubofhubs --env-template .env.example`. Never edit between the markers or type a number into them. The plain words for each check are rows of `docs/reference/evidence-labels.csv`. The README stays under 150 lines; the area detail lives in `docs/reference/registry.md`.
- **Requirements are declared beside every arm** (`REQUIRES` on the class; shared pieces in `hubofhubs/arm_needs.py`; `()` for an arm that needs nothing). A key is `api(...)` with a secret `env(...)` and the official signup, docs and pricing links; a free-tier or rate-limit statement is copied from the vendor's own page, dated, and left out if it cannot be confirmed there. Python requirements name the extra of `pyproject.toml` that provides the module (`tests/test_requirements.py` checks this). `ENVIRON` still works but new arms use `REQUIRES`. A new arm's `REQUIRES` is part of adding it; `docs/reference/requirements-by-arm.md` is its generated view.
- **Docs are in four folders** (`docs/tutorials`, `docs/how-to`, `docs/explanation`, `docs/reference`) with the index `docs/README.md`; `esoi docs check` must pass. Announcement and article drafts live in `drafts/`, outside the docs. The wiki is generated (`esoi docs wiki --out DIR`), never edited.
- **The registry** is `hubofhubs/registry/*.csv`. A capability is a hub connection (a class, counted once), never one service;
  a single service a consumer hand-wires goes in `hub_integrations.csv`. Facts need a dated source; see `docs/how-to/refresh-the-registry.md`.
- **Consumers** hand this package a `Binding`; the package never imports a consumer. Core imports stay stdlib, the package and `esoi` (`tests/test_import_boundary.py`); third-party libraries belong in per-arm extras.
- **No environment reads, one exception.** Only the user-facing entry functions (`assemble`, `run`, `stream`, `needs`) read `os.environ`, through `resolution.process_environment()`, and only when the caller gave no `environ`; every core module takes the mapping (`tests/test_no_environment.py` pins this). Settings are `AssemblyConfig` fields (`selection_environ` is the only environment `esoi` sees). Names are validated, never import paths. A seat is a `typing.Protocol` declared with `@solution(id)` in `hubofhubs/seats.py`; an arm's constructor parameters typed with a seat are its needs. No alias for a renamed package or arm. Read `docs/explanation/resolution-design.md` before changing resolution or assembly.
- **Generic assembly, selection, cascade and checking belong in esoi, not here;** see `evolvable-structure/docs/explanation/what-belongs-where.md` (when unsure, propose the change to Joshua).

## Checks

```bash
PYTHONPATH=../evolvable-structure/implementations/python python3 -m esoi check
python3 -m pytest tests/test_registry.py tests/test_status.py tests/test_evidence_summary.py tests/test_import_boundary.py tests/test_requirements.py tests/test_tutorial.py   # plus the hub's other small test files
python3 scripts/sync_uses.py --check
PYTHONPATH=../evolvable-structure/implementations/python python3 -m esoi docs check
PYTHONPATH=../evolvable-structure/implementations/python python3 -m esoi requirements --package hubofhubs --coherence   # offline; also tests/test_requirements.py. --online needs wheels of hubofhubs and esoi (neither is on PyPI): build them in a throwaway venv under /tmp and set PIP_FIND_LINKS
```

Generic mechanics belong in esoi (`evolvable-structure`) and are edited only on the owner's own prompt, never from here.
