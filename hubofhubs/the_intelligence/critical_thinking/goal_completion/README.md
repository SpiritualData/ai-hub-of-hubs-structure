# Goal Completion

**Purpose:** Check that the goal was met, and that unasked iteration stops when it should.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Goal Completion

Part of [Holding a request to a measure](../README.md)

## Goal Completion (`goal-completion`)

- Out of scope: Judging how good the response is (Response Quality does that) and making the change (the tools do that).
- Delegates to: response-quality, the-tools, the-representatives, guidance, prioritization, judgment-calls
- Entry call: `hubofhubs.run("goal-completion", ...)`
- Selected implementation: Independent review, then the stop rule (`independent_review`)
- Metric: Goals judged met only when they are, and iteration stopped when it should be
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../decision_check/remainder.py) and 234 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Evidence standard | `goal-completion:evidence_standard` | Says a goal is met when the outcome is present, declares no coverage gap, was not refused and holds every requirement of the done-standard, by pure functions over the done-evidence code. On the stop question it is the stop-only-when-met alternative: iterate while the last verdict is not met, whatever the cost. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) |  |
| Outcome is not empty | `goal-completion:nonempty` | Says a goal is met when the outcome is not empty: what a flow with no completion check implies. On the stop question it is the fixed-iteration-cap baseline: two iterations, whatever the evidence says. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) |  |
| Pragmatic stop rule | `goal-completion:pragmatic_stop` | The evidence standard's verdict, and a stop decision by deterministic code: stop when the check says met or the next milestone is reached; obey what the person stated (one pass, keep going until, stop) and the policy and authority that bound the work; ask when only a person can supply what is missing; stop at a ceiling; otherwise continue only while the last iteration closed a worthwhile share of the remaining gap for its share of the remaining budget, and stop on a plateau, an oscillation or a regress. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) |  |
| Independent review, then the stop rule | `goal-completion:independent_review` | A second pass that reads only the last outcome, never the worker's claim nor the verdict it was handed, re-derives whether the goal is met, and then applies the pragmatic stop rule on that reading. It is an arm and not a stage so that the metric can rank it against the rule that trusts the check. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) | selected |
| Fast-tier model judgment of the stop | `goal-completion:fast_tier_stop` | Asks the fast tier, through Model Plumbing, for one of the five decisions on the history, with the rules stated in the prompt, and falls back to the pragmatic rule when the reply is not one of them. Built and marked paid; not measured, because the stop stage has no free way to run a model and a metric run for it is not worth its spend beside two free arms at or near the top. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) |  |

## Metrics

- Goals judged met only when they are, and iteration stopped when it should be (`metric-goal-completion`): leader `independent_review`, 65 of 65 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
