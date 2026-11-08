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
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../decision_check/remainder.py) and 184 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Links held to their evidence | `response-quality:evidence_check` | Finds every link in an answer and reports each one the evidence text does not contain. | [`hubofhubs/the_intelligence/critical_thinking/response_quality/evidence_check.py`](evidence_check.py) | selected |
| Day counts that match the calendar | `response-quality:date_arithmetic` | Checks each 'N days from today' and each 'N days before/after an event (date)' against the dates the text itself states and the turn's own today. | [`hubofhubs/the_intelligence/critical_thinking/response_quality/date_arithmetic.py`](date_arithmetic.py) |  |
| No em dash | `response-quality:em_dash_free` | Finds every em dash in a response; its repair rewrites each with the punctuation its place needs (parentheses, colon, 'to', comma). | [`hubofhubs/the_intelligence/critical_thinking/response_quality/em_dash_free.py`](em_dash_free.py) |  |
| Figures held to their evidence | `response-quality:grounded_figures` | Finds every figure in a response that the evidence text does not hold; its repair takes out the sentence that states one, keeping the rest. | [`hubofhubs/the_intelligence/critical_thinking/response_quality/figure_grounding.py`](figure_grounding.py) |  |

## Metrics

- Balanced score of a response against its quality profile (`metric-response-quality`): leader `date_arithmetic`, 15 of 15 cases

## Problems

- Quality judged by one fixed standard (`hprob-one-quality-standard-for-everyone`): Response quality is usually judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.

## Ideals

- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is high quality by the standard of the person and situation it serves, and good by default for someone who has said nothing yet.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
