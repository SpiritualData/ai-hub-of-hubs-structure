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
are checked by `tests/test_evidence_registry.py`. The per-area row count appears in the generated `docs/registry.md`.
