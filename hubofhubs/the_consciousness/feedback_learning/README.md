# Feedback Learning

**Purpose:** Make what went wrong once change behaviour afterwards: propose edits to specs, metrics and the datasets that measure them, which ESOI Application applies directly unless Judgment Calls decides to ask.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Feedback Learning

Part of [Adapting to the humans the system works with](../README.md)

## Feedback Learning (`feedback-learning`)

- Out of scope: Applying the edit (ESOI Application does that), deciding the profile the person prefers (Representatives own it) and the thresholds for asking (Judgment Calls owns them).
- Delegates to: esoi-application, the-representatives, judgment-calls
- Entry call: `hubofhubs.run("feedback-learning", {'person': '', 'feedback': {}})`
- Selected implementation: Scoped record edit (`scoped_record_edit`)
- Metric: A correction given once is followed afterwards
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../ai_session_experience/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/flow.py`](../ai_session_experience/flow.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/__init__.py`](../ai_session_experience/frontend_interface/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/interface.py`](../ai_session_experience/frontend_interface/interface.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/tests/test_wire.py`](../ai_session_experience/frontend_interface/tests/test_wire.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/wire.py`](../ai_session_experience/frontend_interface/wire.py) and 56 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Kept note | `feedback-learning:kept_note` | Keeps the feedback text as a note for the next reply: the common way, which changes the next answer and proposes no edit, so the person gives the correction again once the note is gone. | [`hubofhubs/the_consciousness/feedback_learning/propose.py`](propose.py) |  |
| Scoped record edit | `feedback-learning:scoped_record_edit` | A correction that names what it concerns (``about``: a record id; ``field``; ``to``: the new value) becomes one edit to that record, scoped to the person who gave it. Feedback that names no target or no new value is returned unresolved with what is missing, because guessing an edit would change behaviour for someone on a misreading. A turn reported as handled badly (structured signals: unmet goal, error, empty reply, work pushed back to the person, unhappy follow-up) becomes one proposed new case for a dataset of badly handled inputs, for a person to prioritise. | [`hubofhubs/the_consciousness/feedback_learning/propose.py`](propose.py) | selected |

## Metrics

- A correction given once is followed afterwards (`metric-feedback-learning`): leader `scoped_record_edit`, 19 of 19 cases

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
