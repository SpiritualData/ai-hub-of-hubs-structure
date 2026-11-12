# research_recorded

Scores a Learning arm on recorded and reused research (`metric-research-recorded-and-reused` of the-learning). Command: `esoi run research_recorded --impl <arm>`.

- **Cases** (`cases.json`, written by `build_cases.py`): 33 scenarios over fixed fake search results and a scripted judge, in nine areas (the ninth, `observed`: a question that informs a decision is recorded from the research a turn already did with no new search and the discipline stated before reading, a quick fact records nothing, a repeat does not duplicate): a first question is complete for its size and linked to the right solution; a related question reuses an earlier investigation with no search; a stale or smaller one is extended in place; an unrelated question is left alone; a quick fact is not burdened; a finding becomes knowledge once and never over a person's text; a fenced investigation stays in its scope; a held knowledge item or a failing store never fails the answer.
- **Weights**: every case weighs the same, and the score is the share of cases passed. This was written with the cases, before any arm was scored; the baseline arm (`systematic_review`, which returns the record and keeps nothing) was recorded first.
- **What is read**: structured facts read from the stores after the run (investigation files, knowledge files, context items) and the searches counted through the search seats, never what the arm says about itself.
- **Cost**: the searches made across the cases of the `reuse` area are the cost the metric reports; reuse is the saving.
- **Baseline for the cases to fail**: `broken/pulls_everything.py` records everything and reuses the newest earlier investigation whatever the question.
- **Not covered**: a real judge on real questions and a consumer's real store; those are the chat replay on a real quest.
