# AI Session Experience

**Purpose:** Let a person watch, steer, stop and resume the AI while it works, and understand and trust what it did, on any surface and with any harness.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > AI Session Experience

Part of [Adapting to the humans the system works with](../README.md)

## AI Session Experience (`terminal-session`)

- Out of scope: How a run is answered (the front door), how a block is worded and drawn (the terminal blocks), what a harness does to the work, a consumer's settings and data model, and any screen that needs a UI library.
- Entry call: `hubofhubs.run("terminal-session", {'lines': ['/quit']})`
- Selected implementation: Live session (reference terminal) (`live_session`)
- Metric: Scripted sessions that end right and requirements met
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/communication.py`](../communication.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](../feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](../feedback_learning/interface.py), [`hubofhubs/the_consciousness/feedback_learning/propose.py`](../feedback_learning/propose.py), [`hubofhubs/the_consciousness/feedback_learning/tests/test_feedback_learning.py`](../feedback_learning/tests/test_feedback_learning.py), [`hubofhubs/the_consciousness/flow.py`](../flow.py) and 43 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Line REPL (ahohs chat) | `terminal-session:line_repl` | Prompts, reads a line, runs it through the front door and draws the interim updates, the answer, the summary of the work and any question as plain text. Commands: /help, /trail, /later, /quit. | [`hubofhubs/the_consciousness/terminal/repl.py`](repl.py) |  |
| Live session (reference terminal) | `terminal-session:live_session` | Runs any harness in a thread and draws its events in place on a terminal (plain lines elsewhere): current steps, a sub-agent tree, messages sent and taken up, a risky step waiting for y or n, elapsed time and cost; Escape or Ctrl-C stops and keeps the session, resume continues it, and the closing report lists what changed. | [`hubofhubs/the_consciousness/terminal/live.py`](live.py) | selected |

## Metrics

- Scripted sessions that end right and requirements met (`metric-terminal-session`): leader `live_session`, 37 of 37 cases

## Problems

- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.
- A person cannot work with the AI while it works (`hprob-a-person-cannot-work-with-the-ai-while-it-works`): While the AI works the person cannot see what it reads, changes and runs or which helper is acting, cannot stop it without losing the work, resume it, send a correction and see it taken up, or approve a risky step before it happens, and each surface and harness does this differently.

## Ideals

- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.
- Work with the AI while it works (`hideal-a-person-can-work-with-the-ai-while-it-works`): A person can watch, stop, resume, steer and approve the AI while it works, and understand what it did, on any surface and with any harness.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
