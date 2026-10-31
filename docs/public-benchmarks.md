# Public benchmarks and standard reporting

Metrics exist to give a decision a number. A public benchmark is used only where it informs a decision a seat actually
faces. The registry is `hubofhubs/registry/public_benchmarks.csv` (55 rows, every seat) and
`hubofhubs/registry/reporting_formats.csv` (16 formats). Every row has a source and the date it was read; a row built from a
research report that was not re-opened says so in `source_quality`, and anything not opened is marked unverified.

## The rule

1. **A public result can feed a metric as a sourced stage** even though we did not run it, with its URL, date, who ran it,
   which model or harness it covered and the benchmark version. It never becomes our number: a vendor figure is shown as the
   vendor's, and a row's `independent` column says `yes` (the operator ran it), `vendor` (the entrant's maker reported it) or
   `no` (provenance unclear, treated as vendor grade).
2. **Null when not covered.** If the public run did not include the arm or the circumstance we care about, the stage is empty.
   It is never estimated, extrapolated from a neighbouring model, or filled from a different benchmark version (the cascade
   rule already used for stages not run).
3. **Triangulate.** Prefer two or more independent sources for one stage. One vendor-reported number is low confidence and
   cannot decide alone. When sources disagree on the order of the arms, say so; do not average them.
4. **Sanity gate.** Our metrics must make sense to a reasonable person. A public-sourced stage is gated by a few cheap cases of
   ours (face validity). If the public ranking contradicts them, report the contradiction and do not select on it.
5. **Run a subset only when the decision needs it and the spend is inside the cap.** Prefer subsets that need no model
   (retrieval recall, classifier strings, local scoring). Nothing here is run by this registry.
6. **Record version and date** with every public value; a new benchmark version is a new stage, not an update.
7. **Mark the rest honestly.** `prior-only` is background (not used to select); `not-useful` has a stated reason: saturated,
   contaminated, vendor-run, stale, or off our circumstance.

`use` values: `metric-input` (sourced, not run by us), `run-subset`, `run-full`, `prior-only`, `not-useful`.
Counts: 5 metric-input, 5 run-subset, 1 run-full, 30 prior-only, 14 not-useful. Most public numbers are priors, and that is the
honest result of this survey.

## Per seat

| Seat | Worth using | Prior only or not useful |
|---|---|---|
| reason-and-answer | Artificial Analysis index as a sourced shortlist stage, gated by tier sanity cases | HELM (maintenance mode), GPQA, HLE, SimpleQA: exam or recall tests, no decision turns on them |
| model-call | Artificial Analysis price and speed columns, sourced with date | none |
| call-a-model | none | Arena (style preference), LiveBench (nothing verified) |
| assemble-the-whole | none | tau2-bench (vendor board, paid user simulator), GAIA (page unreadable) |
| act-in-the-world | SWE-bench Pro rows for model shortlisting under one scaffold | Terminal-Bench (version moved to 4.0, 2.0 rows not mixable), Aider polyglot (eleven months old), METR (not updated), OSWorld (unread); SWE-bench Verified saturated, WebArena stale |
| connect-any-integration | MCP-Atlas model pass rates, triangulated with BFCL | BFCL V4 (call format is the minority of failures), Toolathlon (no primary source) |
| take-in-the-world | none | BrowseComp (vendor), DeepResearch Bench (changing paid judge), browser-agent vendor figures |
| search-backend | none | single-source search accuracy table, one topic |
| know-the-world | run the page-extraction benchmark in full (offline, no model); SciFact as a 20-pair sanity set | LAB-Bench and AstaBench (entrant is the operator), BrainBench, ScienceAgentBench; BixBench stale |
| remember-and-recall | LongMemEval retrieval recall on a small random subset (no model) | LoCoMo not useful (ceiling and lenient judge, reported by a self-published audit); BEAM and DolphinBench vendor; MTEB and BEIR shortlist only |
| context-assembler | none | RULER, context rot (threshold is per model and ours) |
| card-store | none | BEIR (generic lexical versus dense) |
| think-critically | LLM-AggreFact subset scored by a CPU checker | Vectara board (vendor evaluator, private set), FACTS Grounding (unread), judge-reliability sets |
| watch-for-risk | AgentDojo and InjecAgent strings as offline injection cases | garak and content-harm suites not useful (content, not irreversible actions); OWASP list as a checklist |
| hold-the-intents | none | intent label sets and RouterBench: nothing public represents a life-intent hierarchy |
| stay-current | Epoch hub rows (internal versus external, source cited) as the weekly feed | Papers with Code closed |
| keep-it-generic | none | IFEval: the seat's rule is a scan of our own files |

Costs are in the CSV `cost_to_run` column; where a page gave no price it says "not priced". No cost here is estimated.

## What our results can learn from standard formats

Surveyed in `reporting_formats.csv`. Worth a bridge: the Hugging Face `.eval_results` entry (dataset id and task, value, date,
source URL, notes, and a verified badge for runs done with Inspect) is nearly a public row already, and an Inspect log header
(task, model, aggregate scores) is the second reader. Not worth it now: exporting our rows as Inspect logs (we hold aggregates,
a log needs per-case outcomes), MLflow, Langfuse, Phoenix, Weave (servers that duplicate `results.csv`), HELM (maintenance
mode), the OpenAI Evals API (read-only on 2026-10-31, shut down 2026-11-30), Papers with Code (closed).

## The bridge (proposed, not built)

esoi already separates measured from recorded numbers in `metric_results.py` (`SOURCE_MEASURED`, `SOURCE_RECORDED`,
`SOURCE_NOT_APPLICABLE`, with a `disagrees` flag when a measured and a recorded value differ), and `cascade.py` already says a
stage not run is `None`, never an estimate. The smallest change that makes a public result a first-class, honest stage is a
result source type:

1. **Results log (`harness.RESULT_COLUMNS`).** Optional columns `source` (blank means measured by us, or `public`),
   `evaluated_by`, `source_url`, `bench_version`, `score`. A public row has `impl` = our arm that actually is the evaluated
   model or harness, `model` = what was evaluated, `cases_sha` = `public:<benchmark_id>@<bench_version>`, blank cost and calls,
   and `score` (0 to 1) because a published percent has no honest passed count. `leaderboard.pass_rate` reads `score` for a
   public row. No row exists for an arm the public run did not cover, so that stage stays `None`.
2. **Cascade stage kind (`cascade.KEYS`, `matches`).** A stage key `source=public`. `matches` must also test the row's source, or
   a public row (calls blank) would be taken for an offline `real=no` stage. `max-age-days` and a version change expire it as
   they do now. `decide` takes the best public stage into account only when its gate holds, so a public stage cannot outrank
   measured ones by position alone.
3. **Sanity gate.** `gate=sanity`: the public ordering of arms is compared with the nearest earlier measured stage using
   `leaderboard.higher` (a screen on point estimates; it switches nothing, the significance rule does); a contradiction drops the stage from `decide` and `esoi cascade` prints it.
4. **Triangulation report (`metric_results.reconcile`, `cascade.run_cli`).** Add `SOURCE_PUBLIC`; key public rows by source name so
   two sources are never folded into one; reuse `disagrees` for public against measured and public against public. The cascade
   prints per public stage: sources, independent sources, spread, and the flags `single-source`, `vendor-only`, `disagree`.
5. **Readers (outside the library).** A reader for one `.eval_results` entry and one Inspect log header, each producing one
   public row. Estimated at tens of lines each (an estimate, not a measurement).

The change belongs to the esoi library, which is a separate repository: propose it to its owner; this hub does not edit it.
