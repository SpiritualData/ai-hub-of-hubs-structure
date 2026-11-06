# Representatives

**Purpose:** Let an AI act for a person the way that person would want, within the authority the person gave: the worker categories allowed, the data scope (whose data the AI may read), the person's asking policy and quality profile.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Representatives

Part of [Adapting to the humans the system works with](../README.md)

## Representatives (`the-representatives`)

- Out of scope: Deciding when to ask (Judgment Calls does that), learning from feedback (Feedback Learning does that) and translating implied priorities (Prioritization does that).
- Delegates to: judgment-calls, feedback-learning, prioritization
- Entry call: `hubofhubs.run("the-representatives", '')`
- Selected implementation: Declared authority (`declared_authority`)
- Metric: Authority that stays with its person
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](../feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](../feedback_learning/interface.py), [`hubofhubs/the_consciousness/feedback_learning/propose.py`](../feedback_learning/propose.py), [`hubofhubs/the_consciousness/feedback_learning/tests/test_feedback_learning.py`](../feedback_learning/tests/test_feedback_learning.py), [`hubofhubs/the_consciousness/flow.py`](../flow.py), [`hubofhubs/the_consciousness/interface.py`](../interface.py) and 30 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Declared authority | `the-representatives:declared_authority` | Each person's representative is what that person declared; a person with no declaration gets the least authority over their own data only. | [`hubofhubs/the_consciousness/representatives/representatives.py`](representatives.py) | selected |

## Metrics

- Authority that stays with its person (`metric-the-representatives`)

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
