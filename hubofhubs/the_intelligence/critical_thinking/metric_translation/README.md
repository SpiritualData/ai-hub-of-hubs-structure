# Metric Translation

**Purpose:** Make what success means for a request explicit and measurable as a goal record: the metric, its target, the done-standard and the budget (attempts, pieces and model calls) that Delegation and Model Plumbing enforce.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Metric Translation

Part of [Holding a request to a measure](../README.md)

## Metric Translation (`metric-translation`)

- Out of scope: Creating the specs (ESOI Application does that), keeping the objectives (Objectives does that) and checking the result (Goal Completion does that).
- Delegates to: esoi-application, live-objectives, goal-completion
- Entry call: `hubofhubs.run("metric-translation", {'request': 'what is the latest Rust version?'})`
- Selected implementation: Goal record with default budget (`goal_record`)
- Metric: A goal record with a target and a budget
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](../esoi_application/apply.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/tests/test_esoi_application.py`](../esoi_application/tests/test_esoi_application.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../goal_completion/__init__.py) and 170 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Goal record with default budget | `metric-translation:goal_record` | Turns a request into a goal record: met when the response addresses the request, within the default budget or what its parent has left. | [`hubofhubs/the_intelligence/critical_thinking/metric_translation/translation.py`](translation.py) | selected |

## Metrics

- A goal record with a target and a budget (`metric-metric-translation`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
