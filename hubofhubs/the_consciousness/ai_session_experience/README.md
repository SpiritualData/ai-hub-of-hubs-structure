# Working with the AI while it works

**Vision statement:** A person works with the AI while it works: they see what it does and which structure it serves, and can stop, steer and approve, on any surface and with any harness.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Working with the AI while it works

This sub-intent arises as the implementation `ai-session-experience:composition` of its parent intent [`the_consciousness`](../README.md). Opportunities: The terminal, a separate frontend and the view of how ESOI is involved each improve on their own measure without changing the contract between a harness and a surface, so a new surface or a better way to show sub-agents on solutions never needs a new harness adapter.

## How the solutions fit together

AI Session Experience keeps one contract: typed events going out of a run and typed controls going back, with the adapters that make any harness satisfy it. Structure In View reads the events and the ESOI records and shows which solutions the AI is working on, which sub-agent is on which, and, only when a person opens a solution, its fields and connections. Frontend Interface carries the events, the controls, the run facts and that structure as plain data for a separate web or mobile frontend. Terminal Experience is the reference surface: it draws the run and the structure as lines, reads keys and is the interactive entry.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Frontend Interface](frontend_interface/README.md) (solution with implementations): Let any frontend that is not a terminal draw and steer an AI session from plain data, without knowing the harness or the terminal.
- [Structure In View](structure_in_view/README.md) (solution with implementations): Let a person see which solutions the AI is working on and what each sub-agent does there, on any interface, with detail only when they look for it.
- [Terminal Experience](terminal_experience/README.md) (solution with implementations): Let a person converse with the hub and watch, stop, resume and steer the AI from a plain terminal, with any harness.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Frontend Interface | `frontend-interface` | `hubofhubs.run("frontend-interface", ...)` | Plain JSON picture of the session (`json_wire`) | Every event and control reaches a frontend as plain data, with the run facts and no terminal leaks |
| Structure In View | `structure-in-view` | `hubofhubs.run("structure-in-view", ...)` | Agents arranged by solution, records read on request (`event_tree`) | Right solution per sub-agent, detail only when opened |
| Terminal Experience | `terminal-session` | `hubofhubs.run("terminal-session", {'lines': ['/quit']})` | Live session (reference terminal) (`live_session`) | Scripted sessions that end right and requirements met |

## Problems and ideals

**Problems**

- A separate frontend cannot draw the AI session (`hprob-a-separate-frontend-cannot-draw-the-ai-session`): A web or mobile frontend that is not the terminal cannot show a session: the harness events and controls are Python objects, and each consumer's backend invents its own wire, so each screen drops cost, helpers, changed files, the acknowledgement of a steer or the pending question, or carries terminal wording it cannot draw.
- The person cannot see how structure is in the work (`hprob-the-person-cannot-see-how-structure-is-in-the-work`): When sub-agents work on specific solutions, the person cannot tell which solutions are being worked on, which sub-agent is on which, what each does, or what a solution is for and how it connects, so the structure that guides the work is invisible while it runs.
- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.

**Ideals**

- Any frontend draws the session from plain data (`hideal-any-frontend-draws-the-session-from-plain-data`): Any frontend can draw, steer and approve an AI session from plain data that names no harness and no terminal.
- Structure in view, detail one action away (`hideal-structure-is-in-view-and-detail-is-one-action-away`): A person sees at a glance which solutions the AI is working on and what each sub-agent does there, and reaches a solution's fields and connections only by asking.
- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.

## Metrics and their leaders

- Every event and control reaches a frontend as plain data, with the run facts and no terminal leaks (`metric-frontend-interface`): leader `json_wire`, 28 of 28 cases
- Right solution per sub-agent, detail only when opened (`metric-structure-in-view`): leader `event_tree`, 20 of 20 cases
- Scripted sessions that end right and requirements met (`metric-terminal-session`): leader `live_session`, 67 of 67 cases

## Where to go next

- Parent intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_consciousness/ai_session_experience/frontend_interface](frontend_interface/README.md), [hubofhubs/the_consciousness/ai_session_experience/structure_in_view](structure_in_view/README.md), [hubofhubs/the_consciousness/ai_session_experience/terminal_experience](terminal_experience/README.md)
- Records: [intent.csv](intent.csv)

---

## The full record

### Problems

- A separate frontend cannot draw the AI session (`hprob-a-separate-frontend-cannot-draw-the-ai-session`): A web or mobile frontend that is not the terminal cannot show a session: the harness events and controls are Python objects, and each consumer's backend invents its own wire, so each screen drops cost, helpers, changed files, the acknowledgement of a steer or the pending question, or carries terminal wording it cannot draw.
- The person cannot see how structure is in the work (`hprob-the-person-cannot-see-how-structure-is-in-the-work`): When sub-agents work on specific solutions, the person cannot tell which solutions are being worked on, which sub-agent is on which, what each does, or what a solution is for and how it connects, so the structure that guides the work is invisible while it runs.
- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.

### Ideals

- Any frontend draws the session from plain data (`hideal-any-frontend-draws-the-session-from-plain-data`): Any frontend can draw, steer and approve an AI session from plain data that names no harness and no terminal.
- Structure in view, detail one action away (`hideal-structure-is-in-view-and-detail-is-one-action-away`): A person sees at a glance which solutions the AI is working on and what each sub-agent does there, and reaches a solution's fields and connections only by asking.
- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Frontend Interface | `frontend-interface` | Plain JSON picture of the session (`json_wire`) | Every event and control reaches a frontend as plain data, with the run facts and no terminal leaks |
| Structure In View | `structure-in-view` | Agents arranged by solution, records read on request (`event_tree`) | Right solution per sub-agent, detail only when opened |
| Terminal Experience | `terminal-session` | Live session (reference terminal) (`live_session`) | Scripted sessions that end right and requirements met |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Plain JSON picture of the session | `frontend-interface:json_wire` | [hubofhubs/the_consciousness/ai_session_experience/frontend_interface/wire.py](frontend_interface/wire.py) |  |
| Event deltas for a live stream (not built) | `frontend-interface:event_deltas` |  |  |
| Agents arranged by solution, records read on request | `structure-in-view:event_tree` | [hubofhubs/the_consciousness/ai_session_experience/structure_in_view/tree.py](structure_in_view/tree.py) |  |
| Whole delegation tree from the records (not built) | `structure-in-view:records_overlay` |  |  |
| Line REPL (ahohs chat) | `terminal-session:line_repl` | [hubofhubs/the_consciousness/ai_session_experience/terminal_experience/repl.py](terminal_experience/repl.py) |  |
| Live session (reference terminal) | `terminal-session:live_session` | [hubofhubs/the_consciousness/ai_session_experience/terminal_experience/live.py](terminal_experience/live.py) |  |
| Textual session (full-screen terminal) | `terminal-session:textual_session` | [hubofhubs/the_consciousness/ai_session_experience/terminal_experience/textual_session.py](terminal_experience/textual_session.py) |  |

### Metrics

- Every event and control reaches a frontend as plain data, with the run facts and no terminal leaks (`metric-frontend-interface`): `esoi run frontend_interface --impl json_wire`
- Right solution per sub-agent, detail only when opened (`metric-structure-in-view`): `esoi run structure_in_view --impl event_tree`
- Scripted sessions that end right and requirements met (`metric-terminal-session`): `esoi run terminal_session --impl line_repl`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
