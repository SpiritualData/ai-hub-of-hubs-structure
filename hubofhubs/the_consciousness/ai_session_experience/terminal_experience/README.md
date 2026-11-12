# Terminal Experience

**Purpose:** Let a person converse with the hub and watch, stop, resume and steer the AI from a plain terminal, with any harness.

Breadcrumb: [Top](../../../../esoi/README.md) > [Adapting to the humans the system works with](../../README.md) > [Working with the AI while it works](../README.md) > Terminal Experience

Part of [Working with the AI while it works](../README.md)

## Terminal Experience (`terminal-session`)

- Out of scope: The contract of events and controls and the harness adapters (AI Session Experience), plain data for a separate frontend (Frontend Interface), choosing which structure to show and what is inside it (Structure In View), how a run is answered (the front door), and a consumer's own commands, data and words, which stay in its binding (`commands`, `segments`, `panels`, `front_door`, `represent`, `records`).
- Entry call: `hubofhubs.run("terminal-session", {'lines': ['/quit']})`
- Selected implementation: Live session (reference terminal) (`live_session`)
- Metric: Terminal screen as drawn (presentation) after the correctness gate, Scripted sessions that end right and requirements met
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__init__.py`](../acp_agent/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__main__.py`](../acp_agent/__main__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/mapping.py`](../acp_agent/mapping.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/server.py`](../acp_agent/server.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/tests/test_acp_agent.py`](../acp_agent/tests/test_acp_agent.py) and 82 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Line REPL (ahohs chat) | `terminal-session:line_repl` | Prompts, reads a line, runs it through the front door and draws the interim updates, the answer, the summary of the work and any question as plain text. Commands: /help, /trail, /later, /quit. | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/repl.py`](repl.py) |  |
| Live session (reference terminal) | `terminal-session:live_session` | Runs any harness in a thread and draws its events in place on a terminal (plain lines elsewhere): current steps, a sub-agent tree, messages sent and taken up, a risky step waiting for y or n, elapsed time and cost; Escape or Ctrl-C stops and keeps the session, resume continues it, and the closing report lists what changed, what is left and the command that resumes. The structure tree (Tab, arrows) and the authority in force open only on request; the header shows spend and time against the ceilings; the soft limit and the hub's stop decision are one line each; a typed line after a run continues the session and `/harness` switches harness between runs (`WorkTerminal`, `ahohs work`). | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/live.py`](live.py) | selected |
| Textual session (full-screen terminal) | `terminal-session:textual_session` | The shared session driver drawn as a full-screen Textual application (MIT licence): a header, a scrolling transcript of the run, a live panel with the current steps, helpers and structure, an input line with history and slash-command completion, a question answered by one key, Escape to stop and keep the session, a steer shown as queued then taken up (the transcript keeps what finished, the panel only what is running now), and the final answer rendered as markdown with the rich library. One application stays open across follow-ups and harness switches (`ahohs work`); headless it writes the transcript to the stream it is given. | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/textual_session.py`](textual_session.py) |  |
| Polished session (full-screen terminal with the settled screen rules) | `terminal-session:polished_session` | The shared session driver drawn on a polished full-screen Textual application, brought down from a consumer's long-polished terminal and driven only by the hub's own contract (session events in, typed controls out): the prompt docked at the bottom, a transcript that follows the newest output until the person scrolls away and selects text by dragging, one activity row with a clock once a wait passes three seconds, a calm per-run work panel (about three rows a run, tighter with more runs) and a run detail with the full history and a follow toggle, a note typed while the AI works shown as the person's own line and counted until taken up (several notes combine into one next message, a stopped run flushes them, a failed run starts no new message, and a note is never sent as the answer to a question not yet read), one closing line from structured fields only with the metric before and after shown once above it, warnings folded to one short line each with the rest in a log file, a key line of whole hints (Esc only while the AI works), a command menu with slash completion, and Ctrl+C that copies, stops, or asks twice to quit. A consumer binds its own commands, header segments, panel rows, metric lines, saving and menu choices through the options of `WorkTerminal` and the arm's constructor. | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/polished/session.py`](polished/session.py) |  |
| ACP client session (an existing agent terminal draws the hub) | `terminal-session:acp_client_session` | An installed open-source ACP terminal client, by default Toad, is launched as a separate program on the person's terminal and pointed at `ahohs acp`, which serves the hub's session harness over the Agent Client Protocol (JSON-RPC 2.0 on stdio): each step is a tool call updated in place by its step id (read, edit and run kinds mapped), each helper a tool call titled with the helper and its solution, the solution, milestone, who the AI acts for, the ceilings and the metric before are the first message and plan, a risky step is a permission request showing its preview (approve or refuse), session/cancel is Stop, session/load is Resume, the hub's `_session/steering` extension is Steer (shown as taken up in a message line), and the closing report with the changed files and the metric after is the last message and the stop reason. The client command is set by the option client or the environment variable AHOHS_ACP_CLIENT; without Toad on the path or the SDK installed the arm is reported unavailable and the best-measured arm stands in, with the reason. | [`hubofhubs/the_consciousness/ai_session_experience/terminal_experience/acp_client_session.py`](acp_client_session.py) |  |

## Metrics

- Scripted sessions that end right and requirements met (`metric-terminal-session`): leader `live_session`, 58 of 58 cases
- Terminal screen as drawn (presentation) after the correctness gate (`metric-terminal-presentation`): leader `live_session`, 7 of 7 cases

## Problems

- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.
- The same update is shown twice while the AI works (`hprob-the-same-update-is-shown-twice-while-the-ai-works`): While a run is in progress the same update appears at the bottom and at the top of the terminal: in the full-screen arm each finished step, helper and queued message was written to the transcript and kept in the live panel, and in the reference terminal a row wider than the screen wrapped, so the in-place redraw erased too few rows and left the previous frame above the new one.
- Every app rebuilds the terminal rules people settled on (`hprob-every-app-rebuilds-the-terminal-rules-people-settled-on`): An app that polishes its terminal over many rounds of use ends with rules the hub's thin screen does not have: a note typed while the AI works is queued, counted and sent as one next message, a stopped run flushes it and a failed one does not, one closing line comes from structured fields, warnings fold to one line with the rest in a file, a clock shows at every wait over three seconds, the prompt stays at the bottom and everything fits 80 columns.

## Ideals

- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.
- A terminal screen keeps the rules people settled on (`hideal-a-terminal-screen-keeps-the-rules-people-settled-on`): A terminal for working with the AI keeps every rule its users settled on over many rounds of use and any app on the hub gets them without rebuilding them.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Working with the AI while it works](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
