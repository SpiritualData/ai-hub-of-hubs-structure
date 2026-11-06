# feedback_learning

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > feedback_learning

Part of [Adapting to the humans the system works with](../README.md)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Kept note | `feedback-learning:kept_note` | Keeps the feedback text as a note for the next reply: the common way, which changes the next answer and proposes no edit, so the person gives the correction again once the note is gone. | [`hubofhubs/the_consciousness/feedback_learning/propose.py`](propose.py) |  |
| Scoped record edit | `feedback-learning:scoped_record_edit` | A correction that names what it concerns (``about``: a record id; ``field``; ``to``: the new value) becomes one edit to that record, scoped to the person who gave it. Feedback that names no target or no new value is returned unresolved with what is missing, because guessing an edit would change behaviour for someone on a misreading. | [`hubofhubs/the_consciousness/feedback_learning/propose.py`](propose.py) | selected |

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
