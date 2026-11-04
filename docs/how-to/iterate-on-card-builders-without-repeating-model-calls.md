# Iterate on card builders without repeating model calls

A card groups information on one topic from many files, and a builder that writes such cards with a model costs money on every
build. Most of what you learn about a builder does not need the model: you learn it from the saved output of one paid build, from
deterministic builders, and from cases that cost seconds. This page orders the work so that a paid run happens once, for a variant
that has already beaten everything free.

The three components that judge `cards-from-files`, and the one that decides:

| Component | Question | Cases | Role |
|---|---|---|---|
| `needed_set` | are the files a piece of work needed inside the first cards, from a store under 0.25 cards per file? | topic tasks from git history, split in time | decides (`authoritative_metric_id`) |
| `cards_from_files` | is the one needed file among the first three files? | 63 | floor for file finding; a card per file wins it by construction |
| `orientation` | is a file of the target's folder among the first three files? | the same 63 | a free proxy |

The stages are recorded in the `cascading_conditionals` of `metric-cards-topic-needs` (`hubofhubs/recall/metrics.csv`), so the order
below is part of the specification, and `esoi.toml` lists only `cards_from_files/llm_topic_cards` under `paid_arms`.

## Stage 0: free, seconds

Run it after every change to a builder, as often as you like. No model is called; the runner refuses one.

1. A deterministic builder (`cochange_topic_cards`, `import_graph_topic_cards`, or your own in `hubofhubs/recall/`) is built and scored
   on all three components:

       python3 -m esoi run needed_set --impl import_graph_topic_cards
       python3 -m esoi run cards_from_files --impl import_graph_topic_cards
       python3 -m esoi run orientation --impl import_graph_topic_cards

   A variant of a builder is a name, not a file: `cochange_topic_cards@cap=6,min_support=3`.
2. The saved output of a model build is replayed, not rebuilt: `topic_cards_replay` returns the cards of the one paid build
   (`evaluation/cards_from_files/datasets/replays/llm_topic_cards_75f9da90.json`, checked against its sha256 and its corpus pin).
   A change to how cards are selected, ordered or combined with other cards is judged on those saved cards for free. Never run
   `llm_topic_cards` to see such a change.
3. Read the failing cases, not the average. A run that is not recorded stops at the first failing case; `--failed` reruns only the
   cases that failed.
4. Record only when the code is committed: `esoi run <component> --impl <arm> --record`, then `python3 -m esoi select cards-from-files
   --promote`. The free arms beat or do not beat each other on `needed_set`; a store above 0.25 cards per file is disqualified there
   whatever it finds.

Stop here when no free arm improves. Most ideas end at this stage.

## Stage 1: a model builder on a sample of areas

Only when a model builder (or a change to the prompt of `llm_topic_cards`) is worth buying: it must be a variant that is expected to
beat the best free arm of stage 0 on `needed_set`, and the sample must be small.

- First one case, read by hand: `esoi run needed_set --impl <arm> --sample 1` (the stage `one`). Then a sample of the cases, spread
  over the areas of the code: `--sample 10` (the stage `sample`). Each is the prefix of the next, so no run is wasted.
- Put the model's calls behind a cassette where the esoi harness offers one: the first run records each call, a rerun with the same
  prompt replays it for nothing, so a retry after a change to selection or scoring costs nothing. This page does not depend on it;
  without a cassette, change one thing per run and rerun only the failing cases.
- The run is under the metric run policy of the consumer and the model-call budget (`--max-calls`). A model arm is listed under
  `paid_arms` in `esoi.toml`, so `esoi run --stale` never starts it.

## Stage 2: one full paid run

Only for a variant that beat the best free arm on the sample of stage 1. One build serves every case, so one full run costs the price
of one build. Record it, save its cards as a replay dataset (`cards_dataset`), and from then on iterate on the replay in stage 0.

## What the record keeps

The rows of `esoi/results.csv` say which stage a result is (`sample` blank is the full set; `sample:10` is stage 1). A row of the
selected arm on a stage is compared only with rows on the same cases, so a free stage-0 row never stands in for a paid run, and the
waiver of the solution names the decision that is still pending until the stage that decides has a row.
