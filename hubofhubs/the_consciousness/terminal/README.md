# Terminal Session

**Purpose:** Let a person converse with the hub in a plain terminal and always see what it is doing and what it asks.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Terminal Session

Part of [Adapting to the humans the system works with](../README.md)

## Terminal Session (`terminal-session`)

- Out of scope: How a run is answered (the front door), how a block is worded and drawn (the terminal blocks), where a typed answer is sent beyond the next message, and any screen that needs a UI library.
- Entry call: `hubofhubs.run("terminal-session", {'lines': ['/quit']})`
- Selected implementation: Line REPL (ahohs chat) (`line_repl`)
- Metric: Scripted sessions that end right
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/communication.py`](../communication.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](../feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](../feedback_learning/interface.py), [`hubofhubs/the_consciousness/feedback_learning/propose.py`](../feedback_learning/propose.py), [`hubofhubs/the_consciousness/feedback_learning/tests/test_feedback_learning.py`](../feedback_learning/tests/test_feedback_learning.py), [`hubofhubs/the_consciousness/flow.py`](../flow.py) and 35 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Line REPL (ahohs chat) | `terminal-session:line_repl` | Prompts, reads a line, runs it through the front door and draws the interim updates, the answer, the summary of the work and any question as plain text. Commands: /help, /trail, /later, /quit. | [`hubofhubs/the_consciousness/terminal/repl.py`](repl.py) | selected |

## Metrics

- Scripted sessions that end right (`metric-terminal-session`): leader `line_repl`, 14 of 14 cases

## Problems

- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.

## Ideals

- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
