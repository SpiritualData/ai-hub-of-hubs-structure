# Public evidence

`hubofhubs/registry/hub_evidence.csv` holds numbers that other people measured about the libraries and arms in the registry:
token efficiency, speed, quality, cost, reliability, safety and maintenance. It is complementary to our own runs and is never
a result row: nothing here is run by this hub, and a value here never becomes our measurement. The grader that reads these rows
(`esoi.evidence`) is generic and lives in the ESOI library; the hub supplies only this data.

## A row

One row is one number from one source for one candidate. Columns: `evidence_id`, `area`, `seat`, `candidate` (the exact name in
`hub_findings.csv` for that area), `dimension`, `measure`, `value`, `unit`, `better` (higher or lower), `comparator` (what the same
source compared it with), `source_url`, `source_kind`, `run_by_independent`, `method_disclosed`, `n`, `benchmark_status`,
`date_published`, `date_checked`, `confounds`, `note`. A source that only ranks leaves `value` empty and puts the ranking in `note`.

## How a row is judged

Judge it as a scientist would, on the evidence:

1. **Who ran it.** `independent_benchmark`, `replication` and `peer_reviewed` outrank `community_report`, which outranks
   `vendor_reported` and `maintainer_reported`. A vendor figure is the vendor's, whatever the page calls it. The test refuses a
   vendor or maintainer row marked `run_by_independent` yes.
2. **Is the method disclosed**, and what is `n`? A figure with no method is a claim, not a measurement.
3. **Is the benchmark still informative?** `saturated`, `archived` and `contamination_risk` rows say so and are weak for ranking.
4. **Confounds are written down**, for example harness against model, author-run on favourable data, single thread, different
   hardware, cost excluding cache, public test sets.
5. **One source is never enough.** Prefer several sources per candidate and dimension; where two disagree, both rows stay and the
   disagreement is named in `note` (for example the two web search sources, or the two reranker tables).

## Adding a row

Open the URL, confirm the number, unit and date appear on the page, then add the row with `date_checked` set to the day you read
it. A number you cannot confirm is not entered. New descriptive prose in a row is unconfirmed: for Joshua to confirm. The rules
are checked by `hubofhubs/the_world/learning/research_freshness_reader/tests/test_evidence_registry.py`. The per-area row count appears in the generated `docs/reference/registry.md`.

## How the library reads it

The registry csv stays the one source of truth. `esoi/evidence.csv` is derived from it by `python3 scripts/export_evidence.py`
(the library's fixed header: no `area`, no `seat`; a row with no value, a direction only, is left out; a comma in a candidate name
becomes a space). The derived file is committed so a package that builds on the hub can read it, and
`tests/test_export_evidence.py` fails when it differs from the export, so edit the registry and re-run the script, never the
derived file. `esoi.toml` names it under `[evidence]` and maps the candidates that match one of our arms under
`[evidence.aliases]`; `esoi evidence list|grade|rank|table` and `esoi cascade` read it. The `public` stage of the
`context-retriever` and `file-editing` metrics is satisfied only when graded evidence for an arm is at grade C or better, and it
never replaces our own first-stage result.

## From public evidence to a prior per arm

Every solution's `public` cascade stage follows this rule. A solution whose arms are worth ordering before we measure them
keeps a `public_priors.csv` beside its records: one row per arm, with the columns `arm_id`, `harness` (the implementation),
the arm's parameters (for example `provider` and `tier`), `prior`, `grade`, `basis_evidence_ids`, `measure_first`, `reason`,
`date_checked` and `expires`. Delegated Agent Sessions is the first
(`hubofhubs/the_world/tools/delegated_agent_sessions/public_priors.csv`).

1. **What counts.** Only `quality` rows of `hub_evidence.csv` that `esoi evidence grade` puts at C or better, on a benchmark
   whose status is `live`, run no more than 180 days before `date_checked`. Vendor-only, saturated and archived rows never
   set a prior; they may still be named in `basis_evidence_ids` as the reason for `measure_first`.
2. **The prior is a number someone published, never one we estimate.** Resolve the arm to the exact model it runs (for
   example the tier chooser's model for its provider and tier on `date_checked`).
   - *Direct*: a counting row names this implementation (by its candidate or an `[evidence.aliases]` entry) and this model.
     `prior` is its value as a fraction; `grade` is its grade.
   - *Borrowed*: no direct row, but a counting row names this model under another harness, and the same benchmark version holds
     at least two models run under both harnesses whose scores agree within the grader's tolerance for quality (10 percent
     relative). `prior` is the other harness's value; `grade` is one letter below the weaker of the rows used; the reason says
     "Borrowed" and `basis_evidence_ids` lists the comparison rows. One step only: a prior is never borrowed from a borrowed prior.
   - *None*: otherwise `prior` and `grade` stay empty. A neighbouring model, an older benchmark version or a different
     benchmark never fills it.
   - When two counting rows give a direct value and disagree beyond the tolerance, the prior is empty and the reason names both.
3. **How selection uses it.** Our own results always win at the stage they reach: an arm with a measured result is ranked by it,
   and a prior never outranks or averages into a measured result, because a public benchmark's tasks are harder or different
   from our cases and only the order carries over. A prior is used only (a) to order which unmeasured arms to measure first and
   (b) as the labelled fallback ("public prior, grade B") for an eligible arm when no eligible arm has a real result yet. If our
   first real stage orders two arms opposite to their priors by more than the tolerance, both priors are dropped for that
   solution and the contradiction is reported. A priors file may carry `cost_per_case_usd` and `seconds_per_case` (the cost
   and time of one of our cases) only when a source published them for cases like ours; a public benchmark's cost per trial
   is never scaled down to our cases, because the ratio is itself an estimate. Left empty, they score zero in a balanced
   fallback (an unknown price is never free), and our own first run supplies them.
4. **What to measure first.** `measure_first` is `yes` for an arm the consumer can run (its credentials exist) whose prior is
   empty or within the tolerance of the best prior among runnable arms, and `no` for an arm that cannot run here or whose
   prior is below the best by more than the tolerance at no lower cost. An empty prior is a reason to measure, not to skip:
   only our run can say.
5. **Expiry.** A prior expires at `expires`: `date_checked` plus 90 days (leaderboards move with every model release), or
   sooner when a basis row passes 180 days, the benchmark moves to a new version, or the arm's parameters resolve to a
   different model. An expired prior is empty until the boards are read again; re-reading means opening the pages, adding the
   new rows to `hub_evidence.csv` and rewriting the priors file.

The rule is generic and lives here; a solution's metric names it in the `when` of its `public` stage. It is not yet code in
esoi: the library's `public` stage only checks that graded evidence exists for an implementation, not per arm parameter.
