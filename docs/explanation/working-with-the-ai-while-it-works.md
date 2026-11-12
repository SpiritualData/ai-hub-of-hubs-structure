# Working with the AI while it works

The experience of a person beside an AI that is doing deep work: watching it, stopping it, steering it, trusting it, and understanding what is
unusual about it. The hub holds the contract in the AI Session Experience solution of Consciousness
(`hubofhubs/the_consciousness/ai_session_experience/`), with three children: Terminal Experience (the reference terminal), Frontend Interface (the contract
as plain data for a web or mobile frontend) and Structure In View (which solutions the AI is working on, opened only on request). A consumer's terminal, chat page
and task modal consume the same contract. Researched 2026-11-10.

## The requirements

Each requirement is stated once, has a stable id and is testable by a scripted session. Surfaces are scored against these ids: the hub's reference
terminal (`H`), the consumer's own terminal (`T`), the consumer's chat of every type (`C`) and the consumer's AI task modal (`M`).

### Watch and control the work

| Id | A person can... | Test (scripted session) |
|---|---|---|
| X1 | watch the work as it happens: each read, change and command appears as a step with its kind and target | steps appear in order with kind and target before the run ends |
| X2 | see which agent is acting and how far along the run is | the current step and the count of steps and calls are on screen |
| X3 | see cost and time so far, and cost marked unknown when the harness does not report it, never shown as zero | elapsed time shown; a run with no cost report shows "unknown" |
| X4 | stop the run at once (Escape, Ctrl-C, a Stop button) without losing finished work | after the stop, files written so far exist and a session is named |
| X5 | resume what was stopped, without redoing finished work | after resume the run ends met, every earlier step ran once |
| X6 | give feedback while the run works and see it taken up | the message shows as sent, then as taken up, and is in the next model call |
| X7 | see sub-agents as a tree with the right parent | the tree on screen has each helper under the agent that started it |
| X8 | steer or stop one sub-agent, or be told plainly that this harness cannot | the helper stops and the rest goes on, or a notice says it is not available |
| X9 | approve or refuse a risky step, which does not run before the answer | the step is absent while waiting, runs after approve, never runs after refuse |
| X10 | see the result and the files changed | the closing report names the outcome and each changed file |
| X11 | switch harness and see the same screen | the same script on two harnesses gives the same rows and outcome |
| X12 | work the same from a terminal, a chat page and a task modal | the surface consumes the shared events and controls, no private ones |
| X13 | use it without colour or cursor control, and reconnect or replay to the same screen | a non-terminal run has no escape codes; replaying the events redraws the same rows |

### Understand and benefit from what is unique here

| Id | A person can... | Test |
|---|---|---|
| X14 | see which solution and milestone the work serves | the run header names the solution and milestone |
| X15 | see sub-agents follow the solution hierarchy | helpers are named by solution and sit under the solution they serve |
| X16 | see progress that is grounded: counts and targets from the work, not the model's narration | every step row comes from a structural fact (kind, target, state) |
| X17 | see the solution frame and the metric before and after | a finished milestone run shows the metric before, after and the change |
| X18 | read explanations only when asked | no explanatory text on the default screen; one action opens the detail |
| X24 | see the structure of the work as a hierarchy, collapsed until asked: which solution the run and each helper works on | by default one compact line or none; one key shows the tree, the same key hides it, and a helper sits under the solution above it |
| X25 | open one solution in the tree to read its fields and connections | the selected solution shows its purpose, approach, metric and latest value, selected implementation, next milestone, problems, ideals and delegates, and only that solution |
| X26 | see spend and elapsed time against the ceilings, quietly | the header shows "spent of ceiling" and "elapsed of ceiling" when the run has ceilings, and no such segment when it has none |
| X27 | be told once, in one line, that the run is wrapping up and why | the soft limit shows one line naming the ceiling and the share used, and the safe stopping point |
| X28 | see the hub's own decision to go on or stop, with its reason, in one line | each decision is one line, "hub decision: go on" or "stop", with the reason in plain words, and the closing report says what is left |
| X29 | type a follow-up after a run ends and have it continue the same session | the next run is a resume of the session just ended, and does the new work |
| X30 | switch harness between runs and go on with the conversation | the next run is on the new harness, starts a new session with a recap of the earlier run, and an unknown name is refused |
| X31 | start with no goal and be asked for one | one hint line and a prompt; a blank line runs nothing; the typed goal runs |
| X32 | see who the AI acts for, and the authority in force when asked | a quiet header segment names the Representative; the opened view lists worker categories allowed, data scope, asking policy and stated stop limits; a command lists and switches Representatives between runs; with none named nothing extra shows |
| X33 | end a run knowing what was done, what is left and the command that resumes it, plus anything done outside the folder | the closing report names the changed files, a "Left" line, the resume command and an outside-folder report |
| X34 | see each helper with its state, go into one to watch it work, and come back to where you were | the main view lists each helper one level down with its state; entering shows its breadcrumb and live activity; leaving returns to the same view |
| X35 | message one agent or stop only that agent while it works, in a helper or at the top | a typed line and Escape in a helper are aimed at that agent (the harness receives its id); at the top they are the whole run's; the message shows as queued, then taken up |
| X36 | enter a helper's own helpers to any depth, always knowing where you are, with one key up one level | a breadcrumb row at every depth and the same keys at every level |
| X37 | depth never makes the screen worse | at depth 4 the content width, header and footer rows, key hints and the time to enter or leave are within the stated tolerance of depth 1 (no indentation per level, no stacked headers) |
| X38 | a finished helper stays readable, and its result is shown once | it stays in its parent's list, can be entered to read what it did, and its result appears once in the parent |

### Manage risk

| Id | A person can... | Test |
|---|---|---|
| X19 | see what will change before an irreversible step | the question names the effect (the preview) before the answer |
| X20 | see what was blocked or refused and why | a refused or blocked step is listed with its reason |
| X21 | undo or resume after the run ends | a finished or stopped run offers resume, or names what to undo |
| X22 | be asked rarely, and answer a question while the run goes on | an open question does not stop other steps from showing; no question for a step that needs none |
| X23 | not be shown settings they just made, or chrome that repeats what is already visible | the screen never restates a choice the person just made |

## What each surface has today

Read on 2026-11-10 from the code of each surface (the web surfaces read-only; a second pass scores them against these ids). `yes` met, `part` partly,
`no` absent, `?` not checked. H is the hub's reference terminal after this work; its scripted score is in the section on the metric.

| Id | H | T (QAR terminal) | C (Quest AI chat) | M (AI task modal) | What the best open-source terminals do | Ideal |
|---|---|---|---|---|---|---|
| X1 | yes | yes: exec lines rolled into counts, targets in the live line | part: `exec`, `status`, `work_trace` drawn; `read` is emitted and not drawn | part: activity log of started, status, exec, output | Claude Code and Codex show each tool call as a typed item; Aider shows SEARCH/REPLACE blocks | each step with kind and target, replaced in place |
| X2 | yes | yes: elapsed clock, count of files read | part | yes: elapsed clock and token counter | Gemini CLI and Codex report per-turn stats | current step, count, time |
| X3 | yes (unknown marked) | yes since 2026-11-10: cost in the closing line when reported | no | part: tokens only | Claude Code `total_cost_usd`; Gemini CLI stats per model; Aider `/tokens` only | cost so far, unknown never zero |
| X4 | yes | yes: Escape and Ctrl+C keep the session | yes: Stop, cooperative, global | part: Stop is an undo | Claude Code Esc keeps work; Aider Ctrl-C keeps the partial reply; Codex `turn/interrupt` ends interrupted | stop at once, keep work |
| X5 | yes | yes: `/resume`, `--resume`, `--continue` | no for a turn (reconnect replays the stream) | part: pause and resume on the live card only | `claude --resume`, `codex resume`, `openhands --resume` | resume by session, no repeat |
| X6 | yes | part: delivered once and confirmed; the taken-up mark is in the control, not shown as a row | part: queued in memory, no pickup event | yes: claim and seen shown in the timeline | Claude Code queues Enter and sends after tool calls; Codex has `codex queue` | sent, then taken up |
| X7 | yes | yes since 2026-11-10: helpers under their parent when the runner reports them (the hub loop does) | no: one `delegated` event | no | Claude Code shows nested subagents as a tree with a (+N) count | tree with parent |
| X8 | yes (honest when unsupported) | no | no | no | Claude Code `/tasks` then `x` stops one subagent; typing into its transcript takes over | stop or steer one |
| X9 | yes | part: a planner confirm waits between steps | yes: ApprovalCard approve or decline | part: approve and restart | Claude Code names the asking subagent, Esc denies one call; Codex `requestApproval`; opencode permission reply | a step waits for the answer |
| X10 | yes | yes since 2026-11-10: closing line names files changed | no | no | Aider `/diff` and auto-commit; Codex file-change items | files changed, diff on demand |
| X11 | yes | no (harness set in config) | no | no | opencode and Codex expose a server; Toad and Zed use ACP so one screen drives many agents | same screen on any harness |
| X12 | yes | part: consumes the events and the shared run control, not yet the full control set | no | no | opencode TUI, web and editor are clients of one server | one contract, three surfaces |
| X13 | yes | no: Textual only | part: reconnect with `resume_from_event` | part: poll with a 120 s cap | Codex and Claude Code have JSON streams for non-terminal use | plain fallback, replay to same screen |
| X14 | yes (when the harness is framed) | yes since 2026-11-10: "Serves ..." when a run names its solution | ? | ? | none found | run names solution and milestone |
| X15 | yes (events carry the solution) | yes since 2026-11-10: a helper line names its solution | no | no | none found | helpers named by solution |
| X16 | yes | yes: Trail from structural events | yes: work trace | ? | typed items rather than prose | no narration as evidence |
| X17 | yes (Framed harness) | yes: metric lines in the milestone block | ? | ? | none found | before, after, change |
| X18 | yes | yes: detail behind Alt+T and Alt+D | ? | ? | Claude Code transcript mode | detail on demand |
| X19 | yes | part: shown with a question a run waits on; QAR does not gate tools yet | no | no | Codex sandbox and approval modes; Claude Code plan mode | the effect before the step |
| X20 | yes | yes since 2026-11-10: blocked steps listed with the reason; also stopped reasons | ? | ? | Claude Code `permission_denied` event | refused steps with reason |
| X21 | yes | yes: resume | part | part | Aider `/undo` reverts the last commit | resume or undo |
| X22 | yes | no: an ask is answered after the turn | part | part | Claude Code passes background subagent prompts to the main session while it works | answer while the run goes on |
| X23 | yes | ? | ? | ? | none measured | nothing restated |
| X24 | yes: `Tab`, `/tree` | ? | ? | ? | Claude Code `/tasks` lists subagents; none shows the solution hierarchy | a hierarchy of solutions, collapsed |
| X25 | yes: Right, `/open` | ? | ? | ? | none measured | the selected solution's fields |
| X26 | yes | ? | ? | ? | Claude Code and Gemini CLI show spend without a ceiling | spend and time against the ceilings |
| X27 | yes | ? | ? | ? | none measured | one line, with the reason |
| X28 | yes | ? | ? | ? | none measured | one line, with the reason |
| X29 | yes: a typed line after a run | part: `--continue` | ? | ? | `claude --continue`, Aider keeps one chat | the same session |
| X30 | yes: `/harness` | ? | ? | ? | none switches agent harness mid-conversation | a new session with a recap |
| X31 | yes: bare `ahohs` | ? | ? | ? | `claude`, `codex` and `aider` open a prompt | a prompt, no goal needed |
| X32 | yes: `--as`, `/as`, `/who` | ? | ? | ? | none measured | who the AI acts for, and the authority |
| X33 | yes | part | ? | ? | Claude Code prints the resume command at exit | done, left, resume command, outside-folder report |
| X34 | yes: Right, Left, Up and Down | ? | ? | ? | Claude Code lists background agents under the prompt | helper rows, a breadcrumb and a live view |
| X35 | yes: type + Enter and Escape in a helper | ? | ? | ? | Claude Code messages a background agent | a message and a stop aimed at one agent |
| X36 | yes | ? | ? | ? | none measured | any depth, one key up |
| X37 | yes | ? | ? | ? | none measured | the same screen at depth 1 and depth 4 |
| X38 | yes | ? | ? | ? | Claude Code keeps a finished agent's transcript | enter a finished helper, result once |

## What the best open-source terminal agents do, worth adopting

Sources opened 2026-11-10 unless a date is given; "not confirmed" means the page read did not say. The earlier hub page `terminal-harness.md` compares
the same projects as terminals (read 2026-11-01); the registry area `terminal_agent_experience` holds this pass as findings.

| Behaviour | Where | Source |
|---|---|---|
| Escape interrupts and keeps the work; Enter during a run queues the message and it is sent after the current tool calls; Escape does not discard the draft | Claude Code | [interactive mode](https://code.claude.com/docs/en/interactive-mode) |
| Nested subagents as a tree below the prompt with a (+N) count; permission prompts of a background subagent surface in the main session naming it; `x` stops one; typing into its row takes it over | Claude Code | [sub-agents](https://code.claude.com/docs/en/sub-agents) |
| Stream events with `parent_tool_use_id` for helpers, `permission_denied`, a final `result` with `total_cost_usd`; `interrupt()` in the SDK | Claude Code | [headless](https://code.claude.com/docs/en/headless) |
| Typed items (command, file change, MCP call, plan update), `turn/interrupt` ending the turn `interrupted`, approval and user-input requests as events, `exec resume <id>`, `queue` for a message | Codex CLI | [repository](https://github.com/openai/codex) |
| One server, many clients: SSE event stream, `prompt_async`, `abort`, a permission reply with `remember` | opencode | [server docs](https://opencode.ai/docs/server/) |
| Ctrl-C is always safe and the partial reply stays; `/undo` reverts what it committed; `/diff` since the last message | Aider | [commands](https://aider.chat/docs/usage/commands.html) |
| `stream-json` events init, message, tool_use, tool_result, error, result with per-model token stats | Gemini CLI | [headless](https://geminicli.com/docs/cli/headless) |
| Plan mode read-only, act mode default, `--json` agent_event and run_result lines | Cline CLI | [overview](https://docs.cline.bot/cline-cli/overview) |
| Ask before tool calls by default, allow and deny lists, read-only commands unprompted | Crush (source-available licence: not linkable) | [repository](https://github.com/charmbracelet/crush) |
| `--resume [ID]`, `--always-approve` and `--llm-approve`, JSONL headless; the CLI is no longer actively maintained | OpenHands CLI | [reference](https://docs.openhands.dev/openhands/usage/cli/command-reference) |

Not confirmed from the pages read: Codex TUI keys, opencode event names beyond `server.connected`, anything about Goose's live screen, Amp (its manual pages
returned errors). No published study compares these screens; the nearest source is a position poster (grade D), so the metric below is this hub's own.

## Earlier inputs that shaped the requirements

The owner's earlier rules, from the records and design pages of the hub and its consumer and from his standing feedback (private notes are paraphrased, not copied):

| Requirement | Input and where it lives |
|---|---|
| X4, X5, X21 | After any stop or disconnect the AI resumes as if nothing happened; a paused run shows what is done and one Resume action (consumer page `pause-and-resume`); Ctrl+C stops the work first and asks twice before quitting; leaving a voice session never cancels work, Stop is the only cancel |
| X6 | A message sent to a running task must reach it and a queued message must never sit forgotten at the end of a turn (consumer playbook, steering); never disable the input while the agent runs (consumer page `terminal-ux-prior-art`) |
| X1, X2, X3 | Status lines must be true: no "starting" or "retrying" unless it really happens; say "starting" quickly and keep an elapsed clock running through every wait; status lines fit 80 columns |
| X16 | One calm trace per turn, collapsed by default, built from structural facts, counts never above what the run did (consumer page `live-work-trace`; the hub's work trace schema); the closing line comes from structured fields, never the worker's words |
| X10, X17 | A milestone turn does the work the AI can do and shows a before and after metric; bookkeeping is never the output (standing feedback on measurable progress); the finished view shows a code-written before and after, separate from prose |
| X14, X15 | Milestone work follows the solution hierarchy and a solution frame: classify the deliverable, a deep worker follows a skill, completion measures before and after (milestone-work design notes) |
| X9, X19, X22 | Ask a human rarely, only for what only a human has, outward mail, or a large irreversible step; a costly or slow step starts only on confirmation, with time and cost stated; an ask is a real visible record, not chat text; approvals live in the conversation thread |
| X18, X23 | No explanation the person must read on every visit: an info icon, a collapsed row or a first-use hint; do not restate what the controls already show or warn about a deliberate choice |
| X11, X12 | The consumer's standing rule that generic engines move into the hub seat by seat, and that a second consumer's need goes in the library |
| X13 | Logs never on the screen; the transcript is kept apart from rendering so nothing is lost on reconnect |

## What belongs where

| Part | Lives in | Why |
|---|---|---|
| The event and control contract, the adapters from today's runners, the reference terminal, the scripted harnesses and the metric | the hub, AI Session Experience and Terminal Experience (Consciousness) | harness independent and consumer free; a second consumer gets the experience from one line |
| Its settings, its Textual screen, its data model, its words for its own product | the consumer | they know the consumer's product |
| The wire a web page reads | the consumer's backend maps its stream to the same events and the page draws one component | one component for steps, helpers, cost and files in chat and in the task modal |

**Placement decision.** The experience of a person working with the AI while it works was first the `terminal-session` solution widened, not a new solution and not
a sibling. The owner then decided the surfaces are children: AI Session Experience (`ai-session-experience`) is now the parent that keeps the shared contract (events,
controls and the harness adapters), Terminal Experience keeps the id `terminal-session`, the reference terminal and the scripted metric, Frontend Interface
(`frontend-interface`) carries the contract as plain data for a separate frontend, and Structure In View (`structure-in-view`) shows how ESOI is involved in what
the AI is doing. The parent is a sub-intent (`ai_session_experience`) and not only a solution with folders because its parts need their own paragraph saying how
they share one contract; each child is separate because it has its own alternatives and its own metric (a terminal, a wire shape and a tree of solutions fail in
different ways). The text below is the original reasoning for extending before adding. The hub's rule is to extend before adding. Against each sibling: Request Intake takes in what people ask before a run starts; Judgment Calls
decides whether to ask (a decision, not a screen); Prioritization orders what reaches the person; Representatives carry a person's authority and quality
profile; Feedback Learning edits specs from feedback. None of them draws a run or takes a stop, a correction or an approval while it works, and a sibling
would need the same metric and the same arms as Terminal Session. Its id and interface (`Conversing`, entry `converse`) stay, its display name is now
AI Session Experience, its purpose is the whole experience, the interface gains `attend`, and the plain line REPL stays as the baseline arm. The registry caps
seats at 15 groups and the area `terminal_agent_experience` is seated on Terminal Experience, which counts under the group of AI Session Experience.

## The contract

Events a harness emits: `RunStarted` (goal, harness, session, resumed, solution, milestone, frame, metric and its value before), `Step` (kind read, edit,
run, check, tool, delegate, note or message-received; state running, done, failed or blocked), `AgentStarted` (with `parent_id` and solution),
`AgentEnded` (met, unmet, stopped, failed), `Review`, `Waiting` (question, what will change, options), `Usage` (cost, tokens, calls, and the ceilings `ceiling_usd` and `ceiling_seconds` when the run has them), `Notice` (a ceiling reached or a decision of the hub: `kind`
`soft-limit`, `hard-limit`, `decision` with `decision` go on or stop and the `reason` code, or `outside-folder` with `items`) and `Finished` (outcome
met, unmet, stopped or failed; report; files changed; session; what was blocked and why; the metric after; messages never taken up; `end_reason`, `outside`, spend and time).
Controls a surface sends: `Stop`, `Resume`, `Steer`, `Approve`, `Refuse`, each able to name one agent. `Capabilities` says which a harness honours, and a
surface shows the others as not available. `Harness` is two methods: `start(goal, sink, resume_session_id)` and `control(control)`.

Adapters: `LoopLines` (the hub loop's progress strings), `loop_log_events` (helpers from `LoopResult.log`), `StreamJson` (Claude Code stream lines),
`report_events` (a `SolutionReport` tree), `progress_events` (routes one `ProgressEvent`). Harness adapters: `LoopHarness`, `StreamHarness`, `ApprovalGate`
(wraps tools so a risky call waits), `Framed` (adds solution, milestone, frame and a metric before and after to any harness), `Limited` (tells the surface the ceilings, and the spend estimated
while the run works), `Tailed` (gives a runner that does not forward its stream lines the steps of its work, read from the session's own record) and `Briefed` (standing text after the goal that the
screen does not show, such as the recap of an earlier run). `progress_events` also turns a runner's `tokens` tick into `Usage` with the ceilings, and its `status` ticks of phase `soft_limit`,
`hub_resume` and `outside_folder` into `Notice`; a helper whose description starts with `[solution-id]` is placed under that solution.

## What the loop emits

The hub loop reports the contract's own events beside its progress strings (the strings stay for a consumer that reads only text). Each is
`ProgressEvent(type="session", data=<dict>)` (`EVENT_SESSION`), and every dict is the `to_dict` of the event of that name, so a web surface can carry it
as JSON and `event_from_dict` rebuilds it. Fields below are only added to, never renamed.

| `data["type"]` | Fields | When |
|---|---|---|
| `run-started` | `goal`, `harness`, `session_id`, `resumed`, `solution`, `milestone`, `frame` | once, when `work` or `run_goal` starts (the caller gives solution, milestone and frame; `as_solution_worker` passes those of its brief) |
| `step` | `agent_id`, `step_id`, `kind`, `label`, `state`, `detail` | read and edit: once, done or failed. run, use, check and delegate: `running` before the command starts, then the same `step_id` `done` or `failed` (with `detail` on a failure). A command of several lines is named by its first line and how many more |
| `step` with `kind` `message-received` | `label` = the message | when the inbox is drained, so a steer is shown as taken up at the moment the loop has it |
| `agent-started` | `agent_id`, `parent_id`, `task`, `solution` | a `DELEGATE` helper starts under its parent; a solution tree (`work_solution(..., session=sink)`) announces each node under its parent solution |
| `agent-ended` | `agent_id`, `state` (met, unmet, stopped), `calls`, `summary` | the helper or node is done |
| `usage` | `agent_id`, `calls`, `cost_usd`, `tokens` | after each model call: calls so far for the whole tree, cost and tokens so far when the provider reports them (tokens are plain input plus output; cache reads and writes are left out, as in the sibling runner) |

`LoopHarness` reads these and no longer guesses from strings or from `LoopResult.log`. A solution tree is a tree of agents: `work_solution` puts
`agent_id` in each brief and `as_solution_worker(..., emit=)` reports each worker's steps under it (`TreeHarness` in `scripted.py` shows it, and the
metric scores it).

A stop is prompt. With a `cancel` the model call runs on its own thread and is given up as soon as `cancel()` turns true: the Claude CLI call is
ended (its process group is killed, `claude_cli.abandon_thread`), the state saved before the call stays, the call is not counted, and a resume replays it.
Measured on a scripted completion that holds a call for six seconds: a stop took 6.04 seconds to return before, and 0.07 after. A `RunControl` handed to
`run_goal(control=...)` now steers (messages claimed once, confirmed with `mark_seen`) and pauses the loop like the stream runner.

Still open: the stream runner does not forward its raw lines (it should emit each as `ProgressEvent(type="stream", data=<line>)`), the `permission_denied`
line shape the adapter reads is assumed from the event name in the CLI documentation, and one helper of the loop cannot be stopped or steered alone
(`Capabilities.target_agents` is false for the loop).

### Found by a real task, fixed in the loop

A first real multi-step run on a production lane ended incomplete after 13 calls and found four defects. (1) Tokens counted cache reads and writes, about
a hundred times the sibling runner's basis, so a token budget stopped the run: the loop now reports plain input plus output. (2) Each command got a
new `/tmp` and a read-only home: one private scratch folder per session (mode 0700, beside the session file, kept across a resume) is bound at `/tmp`
with `TMPDIR` set, `XDG_CACHE_HOME` points inside it, the real home stays read-only and untouched, and the system text says so in one line. (3) A
command of several lines could not be written: a fenced `bash` or `sh` block is one command, and so is a `RUN:` line that opens a heredoc, with its body
and terminator; a fence inside a `REPORT` or an edit block is text. (4) Every call carried the whole brief: a goal at or above the cache size moves into
the system text (kept first line as the title in the message, when goal and context fit), the history section is bounded near 20,000 characters (older
calls shrink first), and each call logs at INFO the size of the system text and of each message section, then the tokens the call reported.

A second real task ended "the model did not use the action protocol" at a high cost, and its log showed a 230,000-character message at every call, written to the cache
each time (about 82,000 tokens of cache write per call, 32,000 read). Fixed: a system text longer than one argument (about 100 KB) goes to the Claude CLI
through a private file (`--system-prompt-file`, mode 0600, removed after the call; the runner's `system_chars` setting, default 300,000, says how much stable
content it may hold). Everything that does not change during a run lives in it, in this order: instructions, goal, context, the folder map as it was at the
start, the start files; the message holds a one-line goal title, files changed or added since, the history and the note. The view is one budget
(`view_chars`): files the goal names, then the Folder View's picks, then files only the context names; what does not fit is listed in the map as a file to
READ. A reply with no action is nudged every time it follows one that acted, the run ends only after two in a row (not met, with the last NOTE, resumable),
and long prose after work was done is a REPORT candidate. `usage` events carry `cache_read_tokens` and `cache_write_tokens`, and a run ends with one totals
line. Measured live on the shape of that run (goal 24,000 and context 44,000 characters naming 20 files of 8,000): cache write per call 98,036, 72,671,

A third real task showed caching working (21 calls, cache read 1,235,840, cache write 314,078) and still produced nothing: the model wrote no NOTE, forgot what it had
learned, ran one failing command nine times and could not pass a check only a person could satisfy. Fixed: the model keeps a `STATE:` block (done, learned
with the facts, next, failed) that the loop shows at the top of every message and keeps in the saved session (4,000 characters, the latest replaces the
previous; a `NOTE` adds a line to it; a reply with actions and no STATE gets a reminder). An exact command or tool call that fails twice with the same first
error line is told so, and is not run a third time; a command that keeps succeeding unchanged is called out the third time; a check that fails twice for the
same reason ends the run not met with the model's report (`LoopResult.partial`, the output of the deep result), so the work done is shown. A `READ` may name a file outside
the working folder (read-only, judged by the Folder View's risk rules, so a credentials folder or a key file is refused with the reason, and a missing file is the only one called missing). A
consumer binding can hand the loop its own operations as tools that run in process, and `child_environment` is the one the sibling runners give their worker.
Live, a nine-call task whose fifth step needed a fact printed in the first (after the history was clipped) carried it in STATE and wrote it correctly; the one command that always fails ran twice and was refused the third time.

A fourth task ended incomplete after five loops because the model wrote its actions as function-call markup, which the parser ignored: two such replies in a row
ended the loop and the consumer relaunched cold each time. Now `<invoke name="RUN|READ|CHECK|USE|DELEGATE">` with `<parameter>` bodies (with or without
`<function_calls>`, a stray `<parameter name="command">` as a RUN, multi-line bodies as one command) and a JSON action on a line or in a fenced json block are read as the
same actions, never inside a REPORT or an edit block, and markup that names no action is quoted (120 characters) in what the model is told and in the end reason. Every loop
now ends for a named reason (`LoopResult.ended`, `DeepResult.end_reason`, the totals line): met, blocked, no_action, call_limit, time_limit, cancelled, paused, partial, model_failed
or failed. The wall-clock cap waits for the model call in flight and ends the loop between calls (only a person's stop abandons a call); the consumer's turn limit is the call
limit of one loop; a follow-up with the same `run_id` and no session id resumes a saved session that did not end met, with its STATE and history; the STATE header says how
many calls remain; and one read-only command per reply three times in a row earns a reminder to batch.
72,735, 72,764, 72,830 before; 55,280, 654, 734, 763 after, with the message at about 300 to 500 characters instead of 224,000.

## Run it

`ahohs` (or `python -m hubofhubs.the_self.assembler.cli`) opens the interactive prompt; `ahohs work "<goal>"` runs a goal on a real harness. Both are described in
[Talk to the hub in a terminal](../how-to/talk-to-the-hub-in-a-terminal.md). The scripted demo: `python -m hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live --help`. `--demo loop` runs a scripted session on the hub's own loop, `--demo stream` on a fake
that keeps the stream runner's contract; neither calls a model. On a terminal, Escape or Ctrl-C stops and keeps the session, type `resume` to continue, type
a line to steer, `y` or `n` answers the question, `@name text` steers one helper and `/stop name` stops one. Piped, it prints plain lines and approves
by itself.

### Found by real runs of `ahohs work`

Real runs at the fast tier through a pseudo-terminal (a complete run, Escape then resume, a steer, the structure opened, a follow-up, a switch to another harness) found: the
Claude CLI runners do not forward their stream lines, so a run showed no steps until `Tailed` read them from the session's record; the native runner keeps its sessions in a private
folder, so `Tailed` finds no record for it and its run shows counts and the report but no steps; a helper's own steps and the files it wrote are in a record of their own, so the changed
files list a helper's work only through the helper's row; the session can end `met` while a background helper still runs; with permission mode `acceptEdits` a refused command shows as a
failed step without the reason; a steer is taken up only when the model next reads its input, which took about 15 seconds in a run of many short tool calls; and the first 3 to 4 seconds
of a run show no step at all.

## The metric

`metric-terminal-session` stays the solution's one authoritative metric. Its cases gain the kind `attend` (`evaluation/terminal_session/sessions.py`):
23 scripted sessions (33 with the hub's own parts: structure, ceilings, decisions, follow-up, harness switch, prompt and Representative, in `evaluation/terminal_session/hub_scenarios.py`), each on the hub loop (a scripted completion behind the loop runner) and on a fake of the stream runner, scoring named checks against
the ids above. The number is the share of all 37 cases right (14 line-session cases and 23 attended), balanced with time by the fixed weights; the per-id
shares are reported.

| Arm | Cases right | Balanced | Ids fully met |
|---|---|---|---|
| `line_repl` (baseline) | 24 of 37 | 0.6041 | the ids a plain printed line can show (it prints every event as a line and nothing else) |
| `live_session`, before the loop reported the events itself | 34 of 37 | n/a | the three new cases (a helper announced live, a prompt stop, a solution tree) failed |
| `live_session` | 37 of 37 | 0.9964 | X1 to X23 |
| `live_session`, with the hub's own parts (structure, ceilings, decisions, follow-up, harness switch, prompt, Representative) | 49 of 49 | 0.9969 | X1 to X33 |

`live_session` is selected from this result. What it cannot show: the cases are scripted by the author of the arm, so a ceiling proves the contract holds on
two harnesses and not that a real model's run feels right; X18, X22 and X23 are checked only as the absence of explanations, of a blocked answer and of
restated messages; a person's trial on a real terminal is the next stage.
