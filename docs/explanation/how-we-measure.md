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

1. **The arm with the highest result on the seat's one authoritative metric, at the latest comparable stage, is used by
   default.** Arms are compared only on identical cases (the same case file hash and the same sample).
2. **The page says how firm the lead is.** A lead is labelled *significant* when a one-sided exact paired test on the shared
   cases gives p below 0.05 (exact McNemar for pass or fail per case, an exact sign test for a per-case score, Fisher's exact
   test on aggregates), with Holm's correction across the rivals of the seat. Otherwise it is labelled *best guess, not yet
   significant*. The README evidence table uses these same two labels in its lead column.
3. **An exact tie keeps the current arm.**
4. **A seat or project that serves production users may require significance before switching.** No seat in this repository
   does, so a better arm is used right away and its label says how firm the lead is.
5. **Cost and speed count only through the metric.** The selection rule adds nothing of its own: the seat's metric (which may
   combine pass rate, cost per case and seconds per case with stated weights and a reason) already weighs what matters for
   that seat.
6. **The highest stage is sized so a real difference can reach significance.** The page shows p and the number of cases the two
   arms disagree on, so a reader sees when a stage is too small to settle a question; running the next, larger stage is how it
   is settled, never a hand-picked margin.
7. **Consumers can pin selections** with `esoi lock` and update on their own schedule ([pin selections for production](https://github.com/JoshuaMathias/evolvable-structure/blob/main/docs/how-to/pin-selections-for-production.md)).
8. The selected arm is set from these results by the tool (`esoi select`), never by preference.

## Public evaluations

What others have measured is shown beside our result and never added into it. Each public number keeps its source, date,
who ran it, whether the method is disclosed, its `n`, and its known confounds (`docs/explanation/public-evidence.md`), and is graded by
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
in `esoi/results.csv`, grouped by the area label of their check in `docs/reference/evidence-labels.csv`. Not counted: baselines and floors
(an arm whose module opens with BASELINE, FLOOR, ABLATION or VALIDITY, such as `none` and `single_provider`), and checks with no area
label, which are mechanics of this repository (the single-scenario assembly, the freshness reading, the connection scorer, the
one-call model wrapper). A partial sample run does not count on its own. Arms named by a metric but not yet run are listed under
"What is not measured yet", not counted.

## Reproduce

Every number on the evidence page comes from `esoi/results.csv` and `esoi/per_case.csv`, each row with its commit and
case hash. `esoi run <component> --impl <arm> --record` re-runs one arm; the cases are in `evaluation/<component>/`.
