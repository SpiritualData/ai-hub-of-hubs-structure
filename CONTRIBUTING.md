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

Then run the specific test files for what you changed (for example `hubofhubs/the_self/integrity/tests/test_requirements.py`, `tests/test_import_boundary.py` and the
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

## 5. Research is recorded as an investigation

Research that informs a solution, an arm, a metric or a registry finding is recorded as an investigation in the same pass, before the change it informs. An investigation is
one question, the decision it informs, a method and criteria, the queries with dates and hit counts, what was screened out and why, one item per kept source (with its
URL, grade and what it changed), what is known, contested and unknown, the limitations, a decision for each candidate and a date to revisit
(`hubofhubs/the_world/learning/investigation_record.py` has the standard; `hubofhubs/registry/investigations.csv` has examples).

Write it without editing the CSV files: put the record in a JSON file with `investigation` (the cells of `investigations.csv`) and `items` (one object per kept item; cells
left out are filled) and run

```bash
ahohs investigation record FILE.json        # or, in code: from hubofhubs.api import record_investigation
```

It checks the record against the standard, refuses one with gaps (or `--allow-gaps`) and writes both files. Then name the investigation in the `investigation_id` cell of each
registry finding it produced and link it to the solution it bears on (`links`: `solution:<id>`). Rule L1 of `scripts/esoi_rules.py` (`esoi check`) reads a finding researched
on or after the date in `[rules.L1]` of `esoi.toml` and asks for an investigation that exists, and for a source on every kept item; it is advice until its `fail_from` date,
then a failure. Waive a finding or an item in `waivers.csv` (rule `L1`) with a reason.
