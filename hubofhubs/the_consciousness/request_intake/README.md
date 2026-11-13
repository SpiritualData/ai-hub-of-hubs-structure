# Request Intake

**Purpose:** Take in every request a person makes, once, from wherever the system listens.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Request Intake

Part of [Adapting to the humans the system works with](../README.md)

## Request Intake (`request-intake`)

- Out of scope: Where requests come from (Body's Intake Sources define the adapters), answering them (the flow does that) and what each person is allowed (Representatives do that).
- Delegates to: intake-sources, the-representatives
- Entry call: `hubofhubs.run("request-intake", {'person': ''})`
- Selected implementation: Every declared source (`every_declared_source`)
- Metric: Requests taken in once with their person
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../ai_session_experience/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__init__.py`](../ai_session_experience/acp_agent/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__main__.py`](../ai_session_experience/acp_agent/__main__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/mapping.py`](../ai_session_experience/acp_agent/mapping.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/server.py`](../ai_session_experience/acp_agent/server.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/tests/test_acp_agent.py`](../ai_session_experience/acp_agent/tests/test_acp_agent.py) and 170 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Every declared source | `request-intake:every_declared_source` | Pulls from each declared source (or the ones named), drops a request with no text, a duplicate and a request from another person, and keeps arrival order. | [`hubofhubs/the_consciousness/request_intake/intake.py`](intake.py) | selected |

## Metrics

- Requests taken in once with their person (`metric-request-intake`)

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
