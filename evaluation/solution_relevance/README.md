# Solution relevance cases

Which of the hub's solutions a request, an outside candidate or a bug report concerns, so each gets its own consideration. A
multi-label case: `args.text` in, `expect.gold` the solution ids that needed consideration. Kept apart from `route_a_request`, which
routes a request to an answer kind (information, act, draft, clarify), a different definition of best.

- `hand_cases.json`: requests the hub's consumers send, outside candidates and bug reports, labelled by hand.
- `cases.json`: those plus cases mined from this repository's history by `esoi.understanding.solution_relevance.relevance_cases`
  (`python build_cases.py`).
- `score.py`: the esoi library's shared scorer; this metric builds on the library's `metric-solution-relevance` and adds only these cases.
- `impls/`: the library's two free arms over the hub's records.
