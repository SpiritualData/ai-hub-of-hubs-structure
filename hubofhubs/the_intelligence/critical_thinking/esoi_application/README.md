# ESOI Application

**Purpose:** Apply a proposed edit to the system's own specs and metrics exactly as proposed: an AI is the author of the specs, and the edit is applied directly unless Judgment Calls decides to ask.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > ESOI Application

Part of [Holding a request to a measure](../README.md)

## ESOI Application (`esoi-application`)

- Out of scope: Choosing the metric for a request (Metric Translation does that), proposing edits from feedback (Feedback Learning does that) and deciding whether anyone is asked first (Judgment Calls does that).
- Delegates to: metric-translation, feedback-learning
- Entry call: `hubofhubs.run("esoi-application", {'change': {}})`
- Selected implementation: Record field edit (`record_field_edit`)
- Metric: Edits change exactly the field proposed
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](apply.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](interface.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/tests/test_esoi_application.py`](tests/test_esoi_application.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../goal_completion/__init__.py) and 157 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Append to description | `esoi-application:append_to_description` | Adds the change as a sentence to the end of the record's description: the longer-prompt way, where each correction makes the text longer and no field is edited. | [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](apply.py) |  |
| Record field edit | `esoi-application:record_field_edit` | Sets the one field a change names on the one record it names, or adds one record or milestone once (ensure-one), in the table its kind belongs to (problems, ideals, solutions, implementations, metrics, quality profiles), at the records location it is given. It refuses a change whose target, field or kind does not exist, whose value is empty or carries an em dash, and says why; a refused change leaves every record as it was, and a change the location holds for a person's approval is reported as proposed, never as applied. | [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](apply.py) | selected |

## Metrics

- Edits change exactly the field proposed (`metric-esoi-application`): leader `record_field_edit`, 10 of 10 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
