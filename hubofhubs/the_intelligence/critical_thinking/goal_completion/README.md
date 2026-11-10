# Goal Completion

**Purpose:** Check that the goal was met.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Goal Completion

Part of [Holding a request to a measure](../README.md)

## Goal Completion (`goal-completion`)

- Out of scope: Judging how good the response is (Response Quality does that) and making the change (the tools do that).
- Delegates to: response-quality, the-tools
- Entry call: `hubofhubs.run("goal-completion", ...)`
- Selected implementation: Evidence standard (`evidence_standard`)
- Metric: Goals judged met only when they are
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../decision_check/remainder.py) and 223 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Evidence standard | `goal-completion:evidence_standard` | Says a goal is met when the outcome is present, declares no coverage gap, was not refused and holds every requirement of the done-standard, by pure functions over the done-evidence code. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) | selected |
| Outcome is not empty | `goal-completion:nonempty` | Says a goal is met when the outcome is not empty: what a flow with no completion check implies. | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) |  |

## Metrics

- Goals judged met only when they are (`metric-goal-completion`): leader `evidence_standard`, 14 of 14 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
