# A terminal and harness experience for the hub

Status: design only. No code written, no model run, no evaluation run. Public sources were read on 2026-11-01 and are cited
with that date. Where a fact below could not be confirmed from a source, it says so. Wording of the seat, problem and
metric is proposed, and the owner confirms it before it enters `esoi/` (see section 3).

## 1. What a hub terminal is for

The hub is assembled by code and managed more and more by AIs. A terminal for it has two kinds of reader.

- **An AI that manages the hub** (selects arms, locks versions, checks requirements, runs a measurement). It needs commands that
  never prompt, print one JSON document or one JSON line per event, and set an exit code it can branch on. This reader matters most.
- **A person at a prompt** (in a local terminal, in tmux, or over SSH on a server with no browser). They need to see a run as it
  happens: the work the run did, interim replies, questions that block it, and a way to replay or resume. They need it calm,
  readable at 80 columns, and usable with the keyboard alone.

A consumer such as Quest AI Runner (QAR) already has a 4,300-line Textual interface. The aim is that a second consumer gets the
same experience from one line, and QAR keeps only what is its own.

## 2. Two layers

```
events (ProgressEvent) --> pure renderers --> blocks --> any frontend
                                                     |-- plain text / NDJSON (layer 1, stdlib only)
                                                     |-- Textual app          (layer 2, arm)
                                                     |-- prompt_toolkit + Rich REPL (layer 2, arm)
                                                     `-- an ACP client wrapping another harness (layer 2, arm)
```

### Layer 1: the hub CLI (`ahohs`, a console script)

It delegates to the existing `esoi` commands and adds no new logic of its own. `ahohs select | lock | requirements | run | check
| docs` call the same functions as `esoi ... --package hubofhubs`. Only two commands are new: `ahohs assemble` (shows what
`hubofhubs.assemble()` built and what is in `system.pending`) and `ahohs term` (layer 2).

The contract for AIs, the same for every command:

| Rule | Meaning |
|---|---|
| `--json` | One document on stdout: `{"v":1,"ok":bool,"command":str,"data":{...},"error":null or {"code","message","fix"}}`. Logs go to stderr. |
| Streams | A command that runs for a while prints one JSON object per line (NDJSON) with `seq`, `ts`, `type`, `data`. |
| Exit codes | 0 done, 1 a check failed, 2 bad usage, 3 needs something from the caller (the `fix` says what), 4 a dependency is unavailable. |
| No prompts | Never reads stdin for a question unless attached to a terminal and `--no-input` is absent. A missing answer is exit 3, not a hang. |
| Plain by default | `NO_COLOR` and `TERM=dumb` honoured; no cursor movement when stdout is not a terminal. |
| Stable | Fields are added, never renamed, within `v`. A new `v` is a new document. |

`esoi requirements --json` and `esoi lock --json` already exist (esoi help, read 2026-11-01). `select`, `check` and `cascade`
have no `--json`; wrapping their text would be fragile, so the proposal is to add `--json` to them in esoi itself, because
generic mechanics belong there. Until then `ahohs` calls the Python functions behind them where they are importable.

### Layer 2: the interactive terminal

A run is a stream of `ProgressEvent` objects (`type`, `text`, `step`, `data`). The terminal renders them through pure
functions `render(event, state) -> list[Block]` with no UI import. A `Block` is a small dataclass (kind, text, rows, state,
fold-key). A frontend only draws blocks. The same functions drive layer 1's plain text mode and the tests.

What the renderers must handle (types from `hubofhubs.ports.events`; the work trace shape from `docs/reference/work-trace-event.schema.json`):

| Event | Block | Rule |
|---|---|---|
| `status`, `plan`, `read`, `replan` | one line in a live activity strip | chatter: replaced in place, not kept in the transcript |
| `partial` | text appended to the open answer | streamed chunks of one reply |
| `exec`, `intent` | a running-work row; `intent` is an announcement, never an outcome | `intent` must not be shown as the answer |
| `work_trace` | a step row (kind, label, counts, items, state) | the latest event for a `step_id` replaces earlier ones; unknown kind renders as one generic row; shows only what the projector allowed |
| `interim` | a kept message marked "still working" | folds behind an expander when the final result lands |
| `decision` (an ask) | a highlighted block with the question and the way to answer | blocks the turn until answered or deferred; unknown fields are ignored, not fatal |
| `result`, `milestone`, `done`, `tokens`, `explanation`, `overseer`, `understanding`, `context`, `card_thread`, `mode_signal` | answer, notice, closing line, or a folded detail | the closing line comes from structured fields, never from model wording |
| replay and resume | the same blocks, from a stored log | an action (`/replay`, `/resume`), not only another message |

Replay and resume follow QAR's pause-and-resume design, which is design only today: its Run Log gives each event `seq`, `ts`,
`kind`, `v`, `payload`. The terminal reads any log in that shape and treats an unknown `v` as a warning, not a crash. It also
holds the rules QAR settled after real use: logs never on the screen, an elapsed clock at every wait, Ctrl+C stops work first
and asks before quitting, status lines fit 80 columns, no em dashes on screen.

## 3. The seat and its arms (esoi)

Proposed records, wording unconfirmed and for the owner to approve (the hub's rule: an AI adds ids, links and commands, not prose).

- **Problem:** every consumer re-builds a terminal for AI runs, and each gets streaming, folding, asks and replay slightly
  differently, so the AIs that manage it have no stable text contract.
- **Solution seat:** `converse-in-a-terminal`, a `typing.Protocol` with `run(source, profile)` (interactive) and `render(event,
  state)` (pure). Under the World part of the mind (taking in and handing back to a person). Layer 1 is the seat's shared
  contract, not an arm.
- **Ideals to link:** calm and flicker free; every event visible with its right meaning; usable by an AI without a
  human; works over SSH; one line to adopt; the privacy allowlist is never widened on screen.

### Arms

| Arm | What it is | Why it is a candidate |
|---|---|---|
| `textual_generalized` | QAR's Textual interface with the Quest parts removed (section 5) | exists, in daily use, settled UX rules, headless test harness |
| `repl_prompt_toolkit_rich` | a line REPL: prompt_toolkit input, Rich Live for the strip | smallest to build; best fit for SSH, tmux, `TERM=dumb`, screen readers |
| `acp_wrap` | the hub speaks Agent Client Protocol to an existing harness and renders its updates through the same renderers | would reuse a harness's tool UX; hub events must be mapped in |
| `plain_stream` (floor) | layer 1 text mode only | the baseline every arm must beat |

Not arms: Claude Code (proprietary, already a worker), Crush (FSL), Toad (AGPL); see section 4.

### Metric (one metric for every arm, cascading, cheapest first)

Proposed name `metric-converse-in-a-terminal`. Every arm is given the same recorded logs and the same scripted sessions.

1. **offline, replay.** Real event logs recorded from real runs (a plain answer, a deep run, a run with a web and a paper work
   trace, interim replies then a final result, an ask answered, a paused then resumed run, a failed run) are rendered. Pass
   when every event yields a block with the right meaning (checked against a hand-written expected blocks file per log), the
   latest `work_trace` step replaces earlier ones, `interim` folds, `intent` is never shown as the result, no string outside
   the allowlist appears, and nothing throws. Gate: all cases. Real: no model call, free.
2. **keyboard and SSH.** A scripted session through a pseudo-terminal, once locally and once through `ssh` to localhost inside
   tmux, at 80x24 and 40 columns, with `NO_COLOR`: submit, multi-line input, cancel, answer an ask, `/replay`, `/resume`,
   quit. Pass when each step reaches the expected state with no mouse and no garbled output. Gate: all steps.
3. **time to first paint.** Median of 20 cold starts from the command to the prompt being usable, on the same machine. Reported
   with a bootstrap interval. The scored value is the fraction of runs under a budget the owner sets (a best guess until then).
4. **non-interactive JSON fidelity.** The same logs through `ahohs term --json`: every line parses, validates against the
   published schema, and rebuilds the original event list without loss. Expected to be a tie across arms because layer 1 is
   shared; it is kept so an arm that bypasses layer 1 is caught.

Selection follows the hub's rule: the highest scorer at the latest comparable stage is the default, labelled significant
(exact paired test on the same cases, Holm corrected) or "best guess, not yet significant". A tie keeps the incumbent
(`textual_generalized`). A cheaper arm at 100% on every stage ends the comparison, and costlier arms are not run. Cost and
speed count only through stage 3 and the build cost the owner records, never as a separate rule.

### What public research decides, and what our runs add

The public record helps choose which arms exist, not which wins. Our metric differs from every public one (it renders our
event types), so our runs are the only evidence for the ranking.

- I found no public benchmark or usability study that compares terminal interfaces of AI harnesses. The nearest source is a
  CHI 2026 workshop poster, a position paper and not a measurement
  ([arXiv 2603.10664](https://arxiv.org/abs/2603.10664), found 2026-11-01; I did not read the full text). Grade: D, opinion.
  Public numbers stay beside ours and are never mixed in.
- So the arm list rests on what the sources below show: the pattern all the strong harnesses share (a core that emits typed
  events, a thin UI that draws them, and a non-interactive JSON mode) and which licences can be linked.

## 4. Public research (read 2026-11-01)

Pages were read through a page-to-text fetch of each project's front page or documentation. Releases and versions were empty in
that view, so no version or release date is claimed. Stars are as shown on the day.

| Project | Licence | Language | Streaming and tool calls | Non-interactive and JSON | SSH, tmux | Embeddable | Source |
|---|---|---|---|---|---|---|---|
| Textual | MIT | Python | widgets update in place; used today by QAR | `run_test()` headless with a Pilot; snapshot plugin | any terminal; `textual serve` serves an app in a browser; 37.6k stars | yes, as a library | [github](https://github.com/Textualize/textual), [testing](https://textual.textualize.io/guide/testing/) |
| Rich | MIT | Python | progress and status displays are flicker free | not stated on the page | any terminal; 57.7k stars | yes, library | [github](https://github.com/Textualize/rich) |
| prompt_toolkit | BSD-3-Clause | Python | input, completion, multi-line; not an event renderer | not stated | SSH server support not stated on the page; 10.6k stars | yes, library | [github](https://github.com/prompt-toolkit/python-prompt-toolkit) |
| Ink | MIT | JavaScript | React renderer; lists Claude Code, Gemini CLI and Copilot CLI as users; 40.2k stars | n/a (framework) | any terminal; a screen reader section exists, contents not read | JS only | [github](https://github.com/vadimdemedes/ink) |
| Bubble Tea | MIT | Go | Elm-style loop; 45.6k stars, "over 18,000 applications" | n/a (framework) | any terminal; Wish for SSH exists, not confirmed here | Go only | [github](https://github.com/charmbracelet/bubbletea) |
| Gemini CLI | Apache-2.0 | TS/JS (inferred) | interactive UI; 108.7k stars | `-p`, `--output-format json`, `--output-format stream-json` (NDJSON events) | terminal tool | an app, not a library | [github](https://github.com/google-gemini/gemini-cli) |
| Codex CLI | Apache-2.0 | Rust (inferred from `codex-rs`) | typed items (message, reasoning, command, file change, MCP call, web search) | `codex exec --json` JSONL with `thread.started`, `turn.completed`, `item.*`; resume by session id (from mirrored docs, not the official site) | terminal tool | an app, has an `sdk` folder, not read; 132.7k stars | [github](https://github.com/openai/codex), [exec docs mirror](https://github.com/openai/codex/pull/4583/files) |
| opencode | MIT | TS/JS (inferred) | TUI is a client of a server | `opencode run --format json` raw events; `opencode serve` HTTP; `opencode attach`; `opencode acp` | the attach split suits remote use | server plus clients, SDK listed not documented; 223.8k stars | [github](https://github.com/sst/opencode), [cli docs](https://opencode.ai/docs/cli/) |
| Goose | Apache-2.0 | Rust | extensions over MCP; ACP listed | headless mode not stated on the page | terminal CLI; 56.1k stars; Linux Foundation AAIF project | an app | [github](https://github.com/block/goose) |
| OpenHands CLI | MIT | Python | terminal mode | `--headless` with `--json`; `openhands acp` | terminal | the page says it is no longer actively maintained | [github](https://github.com/OpenHands/OpenHands-CLI) |
| Aider | Apache-2.0 | Python (pip package) | interactive pair programming | scripting mode not found on the page | terminal tool; 49.9k stars | an app | [github](https://github.com/Aider-AI/aider) |
| Crush | FSL-1.1-MIT | Go | MCP over stdio, http, sse | headless mode not documented on the page | terminal; `crush serve` backend | source-available, not OSI | [github](https://github.com/charmbracelet/crush) |
| Toad | AGPL-3.0 (commercial licences offered) | Python on Textual | runs Claude, Gemini, Codex, OpenHands through ACP | not stated | terminal; 3.5k stars | strong copyleft | [github](https://github.com/batrachianai/toad) |
| Claude Code | not confirmed (the repo shows a LICENSE file; its text was not read) | not stated | typed stream | `-p` with `--output-format json` or `stream-json` (with `--verbose` and `--include-partial-messages`) | terminal tool | a binary; an Agent SDK in Python and TypeScript is described in docs | [github](https://github.com/anthropics/claude-code), [headless docs](https://docs.claude.com/en/docs/claude-code/headless) |

Protocols:

- **Agent Client Protocol (ACP).** Standardizes an editor talking to a coding agent, like LSP: JSON-RPC over stdio for local
  agents, HTTP or WebSocket for remote ones (remote still in progress), Markdown text, JSON shapes reused from MCP plus diffs
  ([intro](https://agentclientprotocol.com/overview/introduction), 2026-11-01). A Python SDK exists under Apache-2.0
  (`agent-client-protocol`, 344 stars, [github](https://github.com/agentclientprotocol/python-sdk)); the hub already lists it
  as the `acp` extra. goose, opencode and OpenHands each expose an ACP mode.
- **MCP** is the tool protocol the hub already depends on (`mcp` extra); it carries tools, not a terminal's event rendering.

What the table says, with its limits:

1. Every strong harness separates a typed event stream from its screen and offers a JSON or NDJSON non-interactive mode
   (Gemini, Codex, opencode, OpenHands, Claude Code). That is the design in section 2, now backed by five independent
   projects. It is a design signal, not a measured ranking.
2. For Python, Textual, Rich and prompt_toolkit are the only mature permissive libraries. Ink and Bubble Tea are strong but
   cannot be linked from a Python package.
3. The only reusable open-source harness terminals that are permissive and Python are OpenHands CLI (unmaintained) and Aider
   (an app, not a library). Toad is the only Textual-based ACP client found, and its AGPL licence rules it out as a dependency.
   So the "wrap an existing harness" arm means the hub speaks ACP, not that it embeds someone else's UI.
4. I did not read each project's code, only its front page, so claims about how well each renders streaming are not
   measured here. The ranking waits for stage 1 to 4 above.

## 5. How QAR reuses it

The test for the design is how many lines QAR needs. Target: `hubofhubs.terminal.run(profile=QUEST_PROFILE)`, where the profile
holds only what is QAR's own.

**The customization surface (a `TerminalProfile`):**

| Field | What it holds | Default |
|---|---|---|
| `name`, `ai_label`, `strings` | product name and the words on screen | generic |
| `theme` | colour tokens, not widget styles | a neutral theme, meeting contrast for NO_COLOR and 16 colours |
| `commands` | a registry: name, help line, handler `(session, args) -> list[Block]` | `/help /replay /resume /quit /json` |
| `event_source` | a factory returning an iterator of events for a message | required |
| `ask_sink` | where an answer to an ask goes | required when asks occur |
| `session_store` | save, list and load a session | a file store |
| `hooks` | `on_turn_start`, `on_turn_end`, `closing_line(result)` | built in, from structured fields |

**What is generic in QAR today** (an estimate from line counts and a search for the word "quest" per module; I did not read every
line, and each move is checked file by file):

- Move candidates, about 2,750 lines: `textual_ui_transcript.py` (selection and copy), `textual_ui_prompt.py` (multi-line
  prompt), `textual_ui_widgets.py` (activity strip, clock, deep activity), `textual_ui_deep.py`, `textual_ui_actions.py`,
  `textual_ui_helpers.py`, `interactive_session_tracker.py` (per-run view model), `interactive_session_render.py`,
  `interactive_session_status.py`, and `textual_ui_outcome.py` (pure functions that choose the closing line from structured fields; a
  few Quest words in it become profile strings).
- Mixed, split before moving: `textual_ui_turn.py` (832 lines, the event handling; the event-to-block part is generic, the
  stamping of quests is not), `textual_ui.py`, `textual_ui_control.py`, `textual_ui_startup.py`.
- Stays in QAR: `interactive_session_quests.py` (quest and goal pickers), `command_menu.py` and `textual_ui_commands.py`
  (Quest commands, registered through `commands`), persona and persistence that use Quest records, the Quest client, and all
  branding. The Quest adapters become `event_source`, `ask_sink` and `session_store` implementations.
- QAR's `cli*.py` (the runner's own commands, `operate-from-a-terminal`) stay; only their `--json` and exit-code behaviour
  moves under the layer 1 contract where it is generic.

Order of the move: renderers first (they have tests and no UI import), then widgets, then the app shell. QAR keeps its
current files as thin re-exports until its existing terminal tests pass against the hub copies, so nothing breaks midway.
QAR's tests for the closing line, 80-column status lines and duplicate-output regressions move with the code and become stage 1
cases.

## 6. Licence and dependency handling

- The hub is Apache-2.0. Linkable: MIT, BSD, Apache-2.0. Not linkable: AGPL-3.0 (Toad), source-available FSL (Crush).
  Proprietary tools (Claude Code) are used only as external processes, as the hub already does.
- Core stays standard library plus `esoi`: the `Block` types, the renderers, the plain text writer, the NDJSON writer and the
  CLI contract. `tests/test_import_boundary.py` keeps that true.
- Each arm declares `REQUIRES` on its class, so `esoi requirements --package hubofhubs` and `esoi install` pick it up:
  `terminal-textual = ["textual"]`, `terminal-repl = ["prompt_toolkit", "rich"]`, `acp` already exists. Libraries are imported
  inside the arm, as the other arms do. A version floor is set only after the owner's check of the version that passes stage 1.

## 7. Phased plan

| Phase | Content | Proof | Cost |
|---|---|---|---|
| 0 (smallest first slice) | `Block` types, the pure renderers for the 18 event types, the plain text and NDJSON writers, `ahohs term replay LOG --json` and `--text`, and the JSON envelope with exit codes for `ahohs assemble`. Three recorded logs. No UI framework. | stage 1 and stage 4 pass on the three logs; free | small, stdlib only |
| 1 | `ahohs select/lock/requirements/run/check` delegating to esoi; ask esoi for `--json` on `select` and `check` | the contract tests; a second AI-side script runs them | small |
| 2 | Seat, metric and records proposed to the owner; build `plain_stream` and `repl_prompt_toolkit_rich`; scripted pty and SSH tests | stage 1 and 2 for both | medium |
| 3 | Lift QAR's generic modules into `textual_generalized` behind `TerminalProfile`; QAR switches with re-exports | QAR's own terminal tests pass unchanged; stage 1 to 3 | medium |
| 4 | `acp_wrap` against one agent that speaks ACP; map ACP session updates and permission requests to blocks | stage 1 and 2; only if phase 2 and 3 leave a gap an existing harness fills | medium |
| 5 | Run the cascade, record results, select by metric, label significance | `esoi cascade` output | recorded runs |

## 8. Risks

- **The recorded logs may not cover asks, replay or resume.** Asks and resume are built behind flags or still design only in QAR,
  so real logs for them may not exist yet. Mitigation: mark those cases "written, not recorded" in the results and do not
  count them as real until logs exist.
- **An unchanged QAR UI can regress during the move.** Mitigation: re-exports and its existing tests as the gate.
- **Thin public evidence.** No public study compares these interfaces, and this pass read front pages only. The ranking is
  unproven until our own stages run; the default is a best guess until then.
- **Textual availability.** Textual and Rich come from one commercial maintainer; this pass did not check the company's
  current status. A pure-renderer core limits the damage if the library stalls.
- **Em dashes and privacy on screen.** The renderers must strip em dashes from code-written text and show only the allowlisted
  work trace fields; both are stage 1 checks, not conventions.

## Summary of findings and recommendation

1. No public benchmark compares terminal interfaces of AI harnesses; the closest source is a position poster (grade D), so our own metric decides the ranking.
2. Gemini CLI, Codex CLI, opencode, OpenHands CLI and Claude Code all split a typed event stream from the screen and offer a JSON or NDJSON non-interactive mode, so do that.
3. For a Python hub, only Textual (MIT), Rich (MIT) and prompt_toolkit (BSD-3) are mature and linkable; Ink and Bubble Tea are not usable from Python.
4. No reusable permissive Python harness terminal exists: OpenHands CLI is unmaintained, Aider is an app, Toad is AGPL, Crush is FSL, Claude Code is proprietary.
5. "Wrap an existing harness" therefore means speaking ACP (Apache-2.0 Python SDK, already an extra) and rendering through our renderers.
6. Two layers: an `ahohs` CLI that delegates to `esoi` with a stable `--json` envelope and exit codes, and pure event-to-block renderers any UI draws.
7. Arms: `textual_generalized` (incumbent), `repl_prompt_toolkit_rich`, `acp_wrap`, floor `plain_stream`; one metric: replay fidelity, then keyboard and SSH, first paint, JSON fidelity.
8. About 2,750 of QAR's 4,300 terminal lines look generic and can move; quests, commands, branding and adapters stay behind a small `TerminalProfile`.
9. Start with phase 0: renderers, NDJSON/text replay of three recorded logs, and the JSON contract, with no UI framework and no cost.
10. Risks to watch: no real logs yet for asks, replay and resume; thin public evidence; keep QAR working through re-exports during the move.
