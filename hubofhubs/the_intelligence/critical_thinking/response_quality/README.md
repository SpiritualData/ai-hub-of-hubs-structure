# Response Quality

**Purpose:** Judge a response against the quality profile that applies to this request.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Response Quality

Part of [Holding a request to a measure](../README.md)

## Response Quality (`response-quality`)

- Out of scope: A person's own profile (Representatives own that), context-specific criteria (Guidance owns those), translating implied priorities into weights (Prioritization owns that), updating a profile from feedback (Feedback Learning owns that) and whether the goal was met (Goal Completion).
- Delegates to: the-representatives, guidance, prioritization, feedback-learning, goal-completion
- Entry call: `hubofhubs.run("response-quality", ...)`
- Selected implementation: Links held to their evidence (`evidence_check`)
- Metric: Balanced score of a response against its quality profile
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../goal_completion/goal_completion.py) and 151 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Links held to their evidence | `response-quality:evidence_check` | Finds every link in an answer and reports each one the evidence text does not contain. | [`hubofhubs/the_intelligence/critical_thinking/response_quality/evidence_check.py`](evidence_check.py) | selected |

## Metrics

- Balanced score of a response against its quality profile (`metric-response-quality`)

## Problems

- Quality judged by one fixed standard (`hprob-one-quality-standard-for-everyone`): Response quality is usually judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.

## Ideals

- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is high quality by the standard of the person and situation it serves, and good by default for someone who has said nothing yet.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
