# Terminal Experience

**Purpose:** Let a person converse with the hub and watch, stop, resume and steer the AI from a plain terminal, with any harness.

Breadcrumb: [Top](../../../../esoi/README.md) > [Adapting to the humans the system works with](../../README.md) > [Working with the AI while it works](../README.md) > Terminal Experience

Part of [Working with the AI while it works](../README.md)

## Terminal Experience (`terminal-session`)

- Out of scope: The contract of events and controls and the harness adapters (AI Session Experience), plain data for a separate frontend (Frontend Interface), choosing which structure to show and what is inside it (Structure In View), how a run is answered (the front door), and a consumer's own screen.
- Entry call: `hubofhubs.run("terminal-session", {'lines': ['/quit']})`
- Selected implementation: Live session (reference terminal) (`live_session`)
- Metric: Scripted sessions that end right and requirements met
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/flow.py`](../flow.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/__init__.py`](../frontend_interface/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/interface.py`](../frontend_interface/interface.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/tests/test_wire.py`](../frontend_interface/tests/test_wire.py), [`hubofhubs/the_consciousness/ai_session_experience/frontend_interface/wire.py`](../frontend_interface/wire.py) and 57 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Line REPL (ahohs chat) | `terminal-session:line_repl` | Prompts, reads a line, runs it through the front door and draws the interim updates, the answer, the summary of the work and any question as plain text. Commands: /help, /trail, /later, /quit. | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/repl.py`](repl.py) |  |
| Live session (reference terminal) | `terminal-session:live_session` | Runs any harness in a thread and draws its events in place on a terminal (plain lines elsewhere): current steps, a sub-agent tree, messages sent and taken up, a risky step waiting for y or n, elapsed time and cost; Escape or Ctrl-C stops and keeps the session, resume continues it, and the closing report lists what changed. | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/live.py`](live.py) | selected |

## Metrics

- Scripted sessions that end right and requirements met (`metric-terminal-session`): leader `live_session`, 39 of 39 cases

## Problems

- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.

## Ideals

- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Working with the AI while it works](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
