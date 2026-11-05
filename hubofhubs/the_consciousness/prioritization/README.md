# Prioritization

**Purpose:** Turn the priorities a person implies into ESOI.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Prioritization

Part of [Adapting to the humans the system works with](../README.md)

## Prioritization (`prioritization`)

- Out of scope: Carrying the person's preferences (Representatives do that), turning a request into a metric (Metric Translation does that), long-term nudges (Guidance does that), deciding what is due (Proactivity does that) and whether work may be done unasked (Judgment Calls does that).
- Delegates to: the-representatives, metric-translation, guidance, proactivity
- Entry call: `hubofhubs.run("prioritization", ...)`
- Selected implementation: Stated and carried fields (`stated_fields`)
- Metric: Candidates in the order the stated rules give
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](../feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](../feedback_learning/interface.py), [`hubofhubs/the_consciousness/flow.py`](../flow.py), [`hubofhubs/the_consciousness/interface.py`](../interface.py), [`hubofhubs/the_consciousness/judgment_calls/__init__.py`](../judgment_calls/__init__.py), [`hubofhubs/the_consciousness/judgment_calls/interface.py`](../judgment_calls/interface.py) and 27 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Stated and carried fields | `prioritization:stated_fields` | Orders the candidates by what the person stated and the fields the data carries: what the person pinned first and deferred last, what their feedback implies, the kind in the order the person gave, a blocked item after the unblocked, the person's own rank (ranked first, unranked after), the earlier deadline, the older ask, the more people waiting and the longer since a nudge. Each place has a reason in words and a weighted milestone. | [`hubofhubs/the_consciousness/prioritization/ordering.py`](ordering.py) | selected |
| As given | `prioritization:as_given` | Keeps the order the candidates arrive in and reads nothing from them. | [`hubofhubs/the_consciousness/prioritization/ordering.py`](ordering.py) |  |

## Metrics

- Candidates in the order the stated rules give (`metric-human-prioritization`): leader `stated_fields`, 15 of 15 cases

## Problems

- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People often imply their priorities instead of stating them, so an AI weighs everything the same or guesses.

## Ideals

- Effort follows what the person cares about (`hideal-implied-priorities-reach-esoi`): The system's effort follows what the person cares about most, including what they only imply.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
