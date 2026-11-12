# Frontend Interface

**Purpose:** Let any frontend that is not a terminal draw and steer an AI session from plain data, without knowing the harness or the terminal.

Breadcrumb: [Top](../../../../esoi/README.md) > [Adapting to the humans the system works with](../../README.md) > [Working with the AI while it works](../README.md) > Frontend Interface

Part of [Working with the AI while it works](../README.md)

## Frontend Interface (`frontend-interface`)

- Out of scope: How a screen looks, the transport (a socket, a stream, polling), a consumer's data model and settings, drawing as text (Terminal Experience), and choosing which structure to show (Structure In View, whose result it carries).
- Entry call: `hubofhubs.run("frontend-interface", ...)`
- Selected implementation: Plain JSON picture of the session (`json_wire`)
- Metric: Every event and control reaches a frontend as plain data, with the run facts and no terminal leaks
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__init__.py`](../acp_agent/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__main__.py`](../acp_agent/__main__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/mapping.py`](../acp_agent/mapping.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/server.py`](../acp_agent/server.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/tests/test_acp_agent.py`](../acp_agent/tests/test_acp_agent.py) and 163 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Plain JSON picture of the session | `frontend-interface:json_wire` | The contract's own dict forms for each event and control, and one snapshot folded from the events and controls: status, goal, what the work serves, latest of each step, helpers with parent and solution, cost, files changed, messages with taken-up marks, the open question, the outcome. An unknown event type is kept apart and never stops the picture. | [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/wire.py`](wire.py) | selected |
| Event deltas for a live stream (not built) | `frontend-interface:event_deltas` | Would send each event once as it happens with the change it makes to the picture, so a live page redraws only what changed. | no code yet |  |

## Metrics

- Every event and control reaches a frontend as plain data, with the run facts and no terminal leaks (`metric-frontend-interface`): leader `json_wire`, 28 of 28 cases

## Problems

- A separate frontend cannot draw the AI session (`hprob-a-separate-frontend-cannot-draw-the-ai-session`): A web or mobile frontend that is not the terminal cannot show a session: the harness events and controls are Python objects, and each consumer's backend invents its own wire, so each screen drops cost, helpers, changed files, the acknowledgement of a steer or the pending question, or carries terminal wording it cannot draw.

## Ideals

- Any frontend draws the session from plain data (`hideal-any-frontend-draws-the-session-from-plain-data`): Any frontend can draw, steer and approve an AI session from plain data that names no harness and no terminal.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Working with the AI while it works](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
