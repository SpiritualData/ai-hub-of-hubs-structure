# Render a run in a terminal

Show a run's work, interim replies, questions and stopped reasons in any terminal frontend, without writing the rules again.

The engine is `hubofhubs.stream(input, seat, ...)`: a generator of the same `ProgressEvent` values `hubofhubs.run` returns in `Result.events` and passes to `on_event`, so a terminal loop is `for event in hubofhubs.stream(text): blocks = render(event, state)`, and the CLI (`ahohs run`), a script and the terminal are one call. A run that cannot start yields a `decision` event (id `needs-setup`) naming what to set.

1. Keep one `TerminalState` per conversation: `state = TerminalState(viewer_id=..., shared=False)`. Call `state.new_turn(turn_id)` when a message starts.
2. For each progress event of the run call `blocks = render(event, state)`. Draw each block where its `fold_key` says: a block with the same key as an earlier one replaces it in place, `state == "removed"` takes the place away, an empty key appends. The events handled are `work_trace`, `interim`, `decision` and `result` (for the outcome); any other event returns no blocks.
3. Show `live_line(state)` on one live row while the turn runs (the newest page opened, or nothing).
4. When the turn ends call `settle(state)` and draw the result: the interims folded into one "Earlier updates (n)" row, the one-line summary of the work, and a stopped reason with Continue.
5. Bind keys to the ids in `block.actions`: `expand_trail` and `collapse_trail` (use `toggle_trail`), `show_all_trail`, `expand_updates` and `collapse_updates` (use `toggle_updates`), `not_now` (`fold_ask`), `answer_now` (`unfold_ask`), `send` and `option:N` (a typed line goes to `answer_ask`), `continue` (send `continue_message()` as the next message).
6. Send an answer your own way (a decision resolve call), then call `close_ask(state, resumes=...)`. Say `resumes=True` only when the work is known to pick back up.

`to_text(blocks)` writes any blocks as plain text, which is the floor every frontend can fall back to. A profile that wants other words passes `state.overrides` (a dict from key to sentence).

The words are the Quest app's English, kept equal by `tests/test_terminal_drift.py`: a rule or sentence changed in the app fails that test until `hubofhubs/terminal/` follows. Reference: [Terminal blocks](../reference/terminal-blocks.md). Design: [A terminal and harness experience for the hub](../explanation/terminal-harness.md).
