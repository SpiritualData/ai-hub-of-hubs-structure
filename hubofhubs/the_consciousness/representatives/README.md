# Representatives

**Purpose:** Let each representative act as itself over time: as the person it stands for would want, within the authority that person gave, or as the character it is when no person stands behind it.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Representatives

Part of [Adapting to the humans the system works with](../README.md)

## Representatives (`the-representatives`)

- Out of scope: Keeping and recalling its history, choosing which part a request needs, deciding when to ask, learning from feedback and translating implied priorities.
- Delegates to: judgment-calls, feedback-learning, prioritization, long-term-memory, context-retriever
- Entry call: `hubofhubs.run("the-representatives", '')`
- Selected implementation: Declared authority (`declared_authority`)
- Metric: One identity and authority per representative
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../ai_session_experience/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/flow.py`](../ai_session_experience/flow.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/__init__.py`](../ai_session_experience/frontend_interface/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/interface.py`](../ai_session_experience/frontend_interface/interface.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/tests/test_wire.py`](../ai_session_experience/frontend_interface/tests/test_wire.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/wire.py`](../ai_session_experience/frontend_interface/wire.py) and 63 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Declared authority | `the-representatives:declared_authority` | Each representative is what was declared for it, a person's or a character's; one with no declaration gets the least authority over the asker's own data only, and its data scope never reaches past what the asker may open. | [`hubofhubs/the_consciousness/representatives/representatives.py`](representatives.py) | selected |

## Metrics

- One identity and authority per representative (`metric-the-representatives`)

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
