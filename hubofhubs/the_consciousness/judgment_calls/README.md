# Judgment Calls

*ESOI records kept beside the code in `hubofhubs/the_consciousness/judgment_calls`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The AI system works in alignment with the humans it serves.

These are the solutions of [Adapting to the humans the system works with](../README.md).

## How the solutions fit together

Consciousness is where the system adapts to the humans and policies it works for. Request Intake takes in what people ask through Intake Sources. Representatives are the AI personas that act for a person, carrying that person's authority, data scope, preferences and quality profile. Prioritization turns the priorities a person states or implies into ESOI and puts the work that competes for the person's attention in order. Judgment Calls decides for the person whether to ask, proceed or decline when a step is risky, and how the ask is timed. Feedback Learning proposes edits to specs and metrics, never to prompts. Those edits are applied directly, with no approval step, unless Judgment Calls decides to ask.

## Judgment Calls (`judgment-calls`)

Ask a person only when that person would want to be asked, and decide how: whether the ask blocks or waits, whether it is batched, what may continue meanwhile, and whether a change to specs or a learning step needs an ask at all (by default it does not).

- Entry call: `hubofhubs.run("judgment-calls", {'signal': {'signal': 'proceed'}, 'person': ''})`
- Selected implementation: Per-person severity policy (`severity_policy`)
- Metric: Asked when a person should be asked
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](../feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](../feedback_learning/interface.py), [`hubofhubs/the_consciousness/flow.py`](../flow.py), [`hubofhubs/the_consciousness/interface.py`](../interface.py), [`hubofhubs/the_consciousness/judgment_calls/__init__.py`](__init__.py), [`hubofhubs/the_consciousness/judgment_calls/interface.py`](interface.py) and 27 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Ask about every risk | `judgment-calls:ask_every_time` | [`hubofhubs/the_consciousness/judgment_calls/judgment.py`](judgment.py) |  |
| Per-person severity policy | `judgment-calls:severity_policy` | [`hubofhubs/the_consciousness/judgment_calls/judgment.py`](judgment.py) | selected |

## Metrics

- Asked when a person should be asked (`metric-judgment-calls`): leader `severity_policy`, 72 of 72 cases

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)
