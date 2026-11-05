# Response Quality

*ESOI records kept beside the code in `hubofhubs/the_intelligence/critical_thinking/response_quality`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

A request becomes a metric with a target and a budget, adjustable while the work runs, and the result is held to it: was the goal met, and is the response good for this person.

These are the solutions of [Holding a request to a measure](../README.md).

## How the solutions fit together

Critical Thinking holds a request to a measure. Metric Translation turns the request into a metric with a target value or improvement and a budget, adjustable while the work runs. ESOI Application records that metric as a spec and applies the principles, creating and editing specs and metrics. Goal Completion says whether the goal's condition was met against its done-standard. Response Quality judges the response against the quality profile resolved for the request.

## Response Quality (`response-quality`)

Judge a response against the quality profile that applies to this request.

- Entry call: `hubofhubs.run("response-quality", ...)`
- Selected implementation: Links held to their evidence (`evidence_check`)
- Metric: Balanced score of a response against its quality profile
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../goal_completion/goal_completion.py) and 134 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Links held to their evidence | `response-quality:evidence_check` | [`hubofhubs/the_intelligence/critical_thinking/response_quality/evidence_check.py`](evidence_check.py) | selected |

## Metrics

- Balanced score of a response against its quality profile (`metric-response-quality`)

## Problems

- One quality standard for everyone (`hprob-one-quality-standard-for-everyone`): Response quality is judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.

## Ideals

- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is judged against the quality profile of the person and situation, with a researched default when none is given.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)
