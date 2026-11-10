# Talk to the hub in a terminal

Work with the hub from a terminal in two ways: hand it a goal and watch it work (`ahohs`, `ahohs work`), or hold a conversation line by line (`ahohs chat`). Bare `ahohs` and `python -m hubofhubs.the_self.assembler.cli` are the same command; with no terminal on the output they print the short help instead of opening a prompt.

## Work on a goal

1. In the folder you want the work done in, run `ahohs work "<goal>"`, or `ahohs` alone to be asked for one. The run uses the harness the hub picks for a person at a terminal (`--harness native`, `stream` or `loop` chooses another), the fast tier (`--tier`), and the Claude CLI login you already have.
2. Watch the steps appear: each read, change and command with its target, the helpers under the agent that started them, the messages you sent and whether the run took them up, and a quiet header with the time and spend against their ceilings. Nothing explanatory is shown until you ask.
3. Keys while it works: **Esc** (or Ctrl-C) stops it and keeps the session; type a line and press Enter to steer it (`@name text` steers one helper, `/stop name` stops one); **Tab** shows or hides the structure tree; Up and Down move in the tree, Right opens a solution's fields and connections, Left closes it; **?** on an empty line lists the keys; `y` or `n` answers a question.
4. After a stop, type `resume` to continue or `quit` to leave. When a run ends you see what was done, what is left, anything done outside the folder, and the command that resumes it (`ahohs work --resume SESSION --harness NAME`, run in the same folder). At the prompt a typed line is a follow-up that continues the same session.
5. Between runs: `/harness NAME` switches harness (the next goal starts a new session with a short recap of the last run), `/new` starts a fresh session, `/session` shows its id, `/as NAME` lists or switches who the AI acts for, `/who` shows their authority, `/ask TEXT` sends a line to the hub's front door instead of the run, `/help` lists all of them, `/quit` leaves.

Options: `--folder DIR`, `--resume SESSION`, `--max-spend USD` and `--max-time 90s|30m|2h` (each also `unlimited`; with none given the hub's high defaults stand, a soft limit at 80 percent makes the run wrap up at a safe stopping point and says so in one line, and a hard limit stops it with the work kept and the session resumable), `--permission acceptEdits|skip` (files may be read and changed and a command is refused and listed, or no permission checks), `--solution ID` and `--milestone TEXT` (the solution the work serves: the header, the structure tree and the report name it, and helpers are asked to start their description with `[ID]` so the tree can place them), `--records DIR` (the ESOI records the tree reads; this folder when it has `esoi.toml`), `--as NAME` (act for a Representative) and `--plain` (appended lines, no redrawing; always so when output is not a terminal, where a run needs a goal and ends after it).

When the hub itself decides to go round again or to stop, one line says which and why ("hub decision: stop, it already went round once more"). With `--as`, a quiet header segment names who the AI acts for and the opened tree adds the authority in force: worker categories allowed, data scope, asking policy and the stop limits that person stated.

A consumer supplies only a binding to `WorkTerminal` (import it from `hubofhubs.api`, with `harness_builder` and `default_harness`): its `build(name)` for harnesses, `commands` (extra slash commands), `segments` and `panels` (extra header text and lines), `front_door` (for `/ask`), `represent` and `people` (its Representatives), and `records`.

## Talk line by line

1. Run `ahohs chat` (with `--arm ID=ARM` or `--lock FILE` to choose arms, as `ahohs run` does). The prompt is `> `.
2. Type a line and press Enter. It goes to `hubofhubs.run("hub-of-hubs", line)`, the same call as `ahohs run`. You see the interim updates, the answer, the note when the critic found a problem, then the one-line summary of the work and a stopped reason when there is one.
3. `/trail` shows or hides the groups behind the summary line. `/help` lists the commands.
4. When the hub asks a question it is drawn with its numbered options. Your next line answers it: a number picks that option, any other text is your own answer, and it is sent as the next message. `/later` folds the question without answering it.
5. Leave with `/quit`, Ctrl-D or Ctrl-C. A setup that lacks a key prints what to set and the chat goes on.

The front door takes one input and no history, so each line is its own run. The loop is `LineRepl().converse(front_door, lines, out)` in `hubofhubs/the_consciousness/ai_session_experience/terminal_experience/repl.py`, so a script or a test can drive it with any callable and any text stream. It draws with the blocks of [Render a run in a terminal](render-a-run-in-a-terminal.md).
