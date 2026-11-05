# Metric Translation

*ESOI records kept beside the code in `hubofhubs/the_intelligence/critical_thinking/metric_translation`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

A request becomes a metric with a target and a budget, adjustable while the work runs, and the result is held to it: was the goal met, and is the response good for this person.

These are the solutions of [Holding a request to a measure](../README.md).

## How the solutions fit together

Critical Thinking holds a request to a measure. Metric Translation turns the request into a metric with a target value or improvement and a budget, adjustable while the work runs. ESOI Application records that metric as a spec and applies the principles, creating and editing specs and metrics. Goal Completion says whether the goal's condition was met against its done-standard. Response Quality judges the response against the quality profile resolved for the request.

## Metric Translation (`metric-translation`)

Make what success means for a request explicit and measurable as a goal record: the metric, its target, the done-standard and the budget (attempts, pieces and model calls) that Delegation and Model Plumbing enforce.

- Entry call: `hubofhubs.run("metric-translation", {'request': 'what is the latest Rust version?'})`
- Selected implementation: Goal record with default budget (`goal_record`)
- Metric: A goal record with a target and a budget
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../goal_completion/goal_completion.py) and 140 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Goal record with default budget | `metric-translation:goal_record` | [`hubofhubs/the_intelligence/critical_thinking/metric_translation/translation.py`](translation.py) | selected |

## Metrics

- A goal record with a target and a budget (`metric-metric-translation`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)
