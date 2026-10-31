# How we measure

One ruler for every seat, so that any reader can check why an arm holds its seat.

## The same three numbers for every arm

Every seat has a set of cases and a mechanical check, written before any arm runs. Each arm of the seat runs on exactly
the same cases with the same budget, and we record:

1. **Pass rate**: the share of cases the arm gets right by the seat's check, shown with its 95% Wilson interval.
2. **Cost per passing case** in US dollars, metered by the harness ($0 for local code; a run on a flat subscription is
   counted in calls and marked as such).
3. **Median seconds per case.**

A check is mechanical wherever it can be (an exact answer, a relevant document in the top five, a test that passes). A
seat whose job is judgment may use a model judge only after the judge has been checked against labelled cases, and the
judge's own agreement rate is published beside the result.

## Who wins

The rule is the same for every seat, and pragmatic for each one:

1. Arms are compared only on identical cases (the same case file hash and the same sample), on the seat's one
   authoritative metric (which may combine quality, cost and time with stated weights).
2. **A switch needs a significant improvement where one can be shown.** A challenger replaces the selected arm when it is
   better on the shared cases by a one-sided paired test (exact McNemar for pass or fail per case, an exact sign test for a
   per-case score), p below 0.05, with Holm's correction across the rivals of the seat.
3. **Not shown better means no switch.** The page says how many cases the two arms disagree on and that more cases would
   settle it; running the next, larger stage is how it is settled, never a hand-picked margin.
4. **A best guess where significance is not possible.** When no arm has been chosen yet, or only a single figure exists,
   the better estimate is chosen and labelled "best guess" until the data can say more.
5. **Cost and speed live in the metric.** The selection rule adds nothing of its own: any significant improvement on the
   seat's metric is enough, because the metric already weighs what matters for that seat. A seat or the whole repository
   may set a stricter requirement for switching (a lower p, more shared cases, a later stage), and the page names it.
6. The selected arm is set from these results by the tool (`esoi select`), never by preference.

## Public evaluations

What others have measured is shown beside our result and never added into it. Each public number keeps its source, date,
who ran it, whether the method is disclosed, its `n`, and its known confounds (`docs/public-evidence.md`), and is graded by
`esoi.evidence`. Public results are used in three ways only:

- **To choose which arms enter a seat**: a candidate with strong independent evidence is worth building an arm for.
- **As a check**: if the strongest independent public evidence orders two arms opposite to our result, both are shown and
  the disagreement is stated, with the likely reason (a different circumstance, model or task).
- **As the only evidence, labelled so**, for a seat we have not yet measured.

## Circumstances

The best arm can depend on the model and the harness. Each run records both, and a seat may select a different arm per
circumstance when the results show it (`esoi.circumstances`). "No add-on" is always an arm of an additive seat, so an
add-on has to earn its place over the model and harness as they are.

## What counts as an alternative

The README headline counts distinct arms (an arm that appears in two stages of one area counts once) that have a recorded whole run
in `esoi/results.csv`, grouped by the area label of their check in `docs/evidence-labels.csv`. Not counted: baselines and floors
(an arm whose module opens with BASELINE, FLOOR, ABLATION or VALIDITY, such as `none` and `single_provider`), and checks with no area
label, which are mechanics of this repository (the single-scenario assembly, the freshness reading, the connection scorer, the
one-call model wrapper). A partial sample run does not count on its own. Arms named by a metric but not yet run are listed under
"What is not measured yet", not counted.

## Reproduce

Every number on the evidence page comes from `esoi/results.csv` and `esoi/per_case.csv`, each row with its commit and
case hash. `esoi run <component> --impl <arm> --record` re-runs one arm; the cases are in `evaluation/<component>/`.
