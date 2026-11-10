# Talk to the hub in a terminal

Hold a conversation with the whole hub from a terminal, one line at a time, with its work summary and questions drawn as they happen.

1. Run `ahohs chat` (with `--arm ID=ARM` or `--lock FILE` to choose arms, as `ahohs run` does). The prompt is `> `.
2. Type a line and press Enter. It goes to `hubofhubs.run("hub-of-hubs", line)`, the same call as `ahohs run`. You see the interim updates, the answer, the note when the critic found a problem, then the one-line summary of the work and a stopped reason when there is one.
3. `/trail` shows or hides the groups behind the summary line. `/help` lists the commands.
4. When the hub asks a question it is drawn with its numbered options. Your next line answers it: a number picks that option, any other text is your own answer, and it is sent as the next message. `/later` folds the question without answering it.
5. Leave with `/quit`, Ctrl-D or Ctrl-C. A setup that lacks a key prints what to set and the chat goes on.

The front door takes one input and no history, so each line is its own run. The loop is `LineRepl().converse(front_door, lines, out)` in `hubofhubs/the_consciousness/ai_session_experience/terminal_experience/repl.py`, so a script or a test can drive it with any callable and any text stream. It draws with the blocks of [Render a run in a terminal](render-a-run-in-a-terminal.md).
