# Goal Completion

*ESOI records kept beside the code in `hubofhubs/the_intelligence/critical_thinking/goal_completion`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

A request becomes a metric with a target and a budget, adjustable while the work runs, and the result is held to it: was the goal met, and is the response good for this person.

These are the solutions of [Holding a request to a measure](../README.md).

## How the solutions fit together

Critical Thinking holds a request to a measure. Metric Translation turns the request into a metric with a target value or improvement and a budget, adjustable while the work runs. ESOI Application records that metric as a spec and applies the principles, creating and editing specs and metrics. Goal Completion says whether the goal's condition was met against its done-standard. Response Quality judges the response against the quality profile resolved for the request.

## Goal Completion (`goal-completion`)

Check that the goal was met.

- Entry call: `hubofhubs.run("goal-completion", ...)`
- Selected implementation: Evidence standard (`evidence_standard`)
- Metric: Goals judged met only when they are
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) and 137 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Evidence standard | `goal-completion:evidence_standard` | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) | selected |
| Outcome is not empty | `goal-completion:nonempty` | [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](goal_completion.py) |  |

## Metrics

- Goals judged met only when they are (`metric-goal-completion`): leader `evidence_standard`, 14 of 14 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)
