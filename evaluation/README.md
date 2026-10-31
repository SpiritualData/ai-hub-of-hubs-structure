# Evaluation components

One folder per seat, named by the seat id with underscores (`card_store`, `reason_and_answer`). Each holds `cases.json`,
`score.py` (`score_case(fn, case)`, and `adapt(implementation, meter)` when an arm needs building) and, for baselines,
`impls/`. Results go to `esoi/results.csv` and `esoi/per_case.csv` with the commit and the case hash.

    PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run card_store --impl local_card_store --record

The method every component follows is `docs/explanation/how-we-measure.md`. Components that call a model or the network belong to the
measurement lanes of those seats; the components here are offline and deterministic.
