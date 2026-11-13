# Decision Check

**Purpose:** Give a draft decision to small independent checks that check each other's work, within a declared number of calls.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Decision Check

Part of [Holding a request to a measure](../README.md)

## Decision Check (`decision-check`)

- Out of scope: Judging a reply against a person's quality profile (Response Quality does that), whether the goal was met (Goal Completion does that), producing the draft, and the consumer's evidence, prompts and records of mistakes (the consumer supplies them).
- Delegates to: model-plumbing, response-quality
- Entry call: `hubofhubs.run("decision-check")`
- Selected implementation: Independent views, adjudicated on disagreement (`agreement_check`)
- Metric: Decisions right within a call cap
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](remainder.py) and 255 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Independent views, adjudicated on disagreement | `decision-check:agreement_check` | Runs one short structured call per view in parallel, each shown only its slice of evidence, counts the draft and any vote the consumer holds, and reconciles by agreement; a disagreement goes to one call that sees only the disagreeing views and must quote evidence that code finds in them. For a reply, each span a view lists is confirmed by an independent call and only a confirmed span is rewritten or removed. | [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](agreement.py) | selected |
| Independent views, decided by majority | `decision-check:majority_vote` | Runs one short structured call per view in parallel, each pick standing only with a quote code finds in its evidence; the pick more than half of the opinions hold is the decision, and only a tie goes to the adjudication call. | [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](agreement.py) |  |
| Independent views with known mistakes | `decision-check:agreement_with_known_mistakes` | The agreement check with each view's known-mistake lines in its prompt, most frequent first and within a token cap, and a twin view built on those lines while the call cap allows. | [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](agreement.py) |  |
| One verify call over all the evidence | `decision-check:single_verify` | One call is shown all the evidence at once with the draft and decides; a reply loses the spans it lists. | [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](agreement.py) |  |
| Draft as given | `decision-check:draft_as_given` | The draft stands and no call is made. | [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](agreement.py) |  |

## Metrics

- Decisions right within a call cap (`metric-decision-check`): leader `agreement_check`, 20 of 21 cases

## Problems

- Cheap model decisions are unreliable (`hprob-cheap-model-decisions-unreliable`): A cheap model asked for a decision in one prompt that mixes every kind of evidence (rules, past examples, descriptions, tool records) often picks wrongly, and the pick is seldom checked against the evidence it should rest on.
- The same mistakes repeat (`hprob-same-mistakes-repeat`): A check makes the same kind of mistake again and again, though each one was found (an eval failure, a person's correction, a disagreement that was settled), because the lesson stays in a log and does not reach the prompt.

## Ideals

- Decisions held by independent checks (`hideal-decisions-held-by-independent-checks`): A decision is accepted when small checks that each saw only their own evidence agree, and is settled from quoted evidence or not at all when they do not.
- Found mistakes not repeated (`hideal-found-mistakes-not-repeated`): A mistake found once becomes a short lesson in the check that made it, kept only while the metric says it pays.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
