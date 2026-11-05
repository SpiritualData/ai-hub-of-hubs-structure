# Contributing

This page covers adding an implementation to an existing interface. Terms are in [the glossary](docs/explanation/glossary.md).

## 1. The files

- The class, in its module under `hubofhubs/`, decorated `@implementation("<solution-id>", "<name>")`, with `REQUIRES = (...)` built from
  `hubofhubs/the_self/assembler/arm_needs.py` (`()` if it needs nothing). Constructor parameters typed with an interface from `hubofhubs/seats.py` are its needs.
- A row in the `implementations.csv` beside the code (`hubofhubs/<area>/implementations.csv`, or `hubofhubs/implementations.csv` for an arm that spans areas; `esoi records place --apply` puts it where it belongs). Run `python3 scripts/sync_uses.py` to fill `uses_solution_ids`, and `python3 scripts/sync_uses.py --check` to verify.
- The evaluation folder entry `evaluation/<component>/impls/<name>.py`, which builds the implementation for the cases.
- Third-party libraries go in a per-implementation extra of `pyproject.toml`, never in the core.

## 2. The commands

Run each with `PYTHONPATH=../evolvable-structure/implementations/python`:

```bash
python3 -m esoi run <component> --impl <name>              # a trial run, nothing recorded
python3 -m esoi run <component> --impl <name> --record     # record the result
python3 -m esoi select
python3 -m esoi check --write-docs
python3 scripts/status.py
python3 -m esoi requirements --package hubofhubs --env-template .env.example
```

Then run the specific test files for what you changed (for example `tests/test_requirements.py`, `tests/test_import_boundary.py` and the
tests of your module), never the whole suite.

## 3. How the row gets measured

It runs on the same cases as its rivals. A paired exact test (two-sided McNemar, Holm-corrected across rivals) compares it with each rival,
and the lead is labelled significant or a best guess. The default is the arm with the highest result on all cases, and it changes only when
the metric says so. A held-out split is an opt-in setting (`[selection] holdout`) and is off here.

## 4. Review and ownership

- The esoi library (`evolvable-structure`) and the esoi record fields that carry the owner's wording are edited only by the owner. Propose changes to them.
- Contributors add implementations, cases and registry rows. A registry row needs a dated source ([refresh the registry](docs/how-to/refresh-the-registry.md)).
- Selection follows the metric, never preference.
- The hub core stays standard library plus esoi.
- No consumer-specific content: prompts and settings of a product stay in that product.
- Generated blocks (the README tables, `docs/reference/leaderboard.md`, `docs/reference/evidence-by-arm.md`) are never edited by hand; run `scripts/status.py`.
