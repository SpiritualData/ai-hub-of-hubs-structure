# Terminal blocks

`hubofhubs.terminal` turns a run's progress events into `Block` values. It imports no UI library; its core is the standard library and this package.

## Block

| Field | Meaning |
|---|---|
| `kind` | `line`, `trail_live`, `trail_summary`, `trail_group`, `interim`, `earlier_updates`, `ask`, `stopped`. A frontend may draw an unknown kind as a paragraph. |
| `text`, `title`, `rows` | The words. No em dash ever reaches them (`clean`). |
| `state` | `live`, `settled`, `expanded`, `open`, `folded`, `waiting`, `answered`, `stopped`, `removed`. |
| `fold_key` | The place the block lives. The same key replaces the earlier block; `removed` takes the place away. |
| `style` | `plain`, `muted`, `emphasis`, `warning`: names a frontend maps to its own colours. |
| `actions` | `(id, label)` pairs the person can do with the block. |

## Events and what they give

| Event | Result |
|---|---|
| `work_trace` | The live line (`trail_live`, key `trail`): the newest page opened. Removed when nothing is open. |
| `interim` | The new message open (`interim`, with "Still needed" and "Next"), the earlier ones removed, one `earlier_updates` row folded above it. |
| `decision` with a decision id | An `ask`: for the viewer, "Needs you" with the question, why only them, numbered options and "Not now"; for someone else, "Waiting on <name>". |
| `result` | Remembers `outcome` and `stop_reason` for `settle`. |

`settle(state)` returns the closing blocks: the folded updates, the work summary (`trail_summary`, key `trail`, with `expand_trail` only when opening shows something the line does not), and a `stopped` block with Continue when the run marked the turn stopped with a known reason (`budget`, `stalled`, `attempt_cap`, `tool_fault`).

## Rules each of these keeps (every one is a test)

- The latest work trace event per step replaces the earlier one; a bad event is dropped.
- Counts are honest: a kind with nothing read is left out, a page a search only listed is never called read, and a record is named by its human title only.
- A shared thread (`shared=True`) names only records marked `visible_to_all`.
- The last message of a turn is open; all earlier ones fold into "Earlier updates (n)" with a one-line preview. A replayed message shows once.
- "Not now" folds an ask and leaves it open. An answer is a number (an option) or free text.
- A stopped reason is shown only when the run gave a known one.

## Words and drift

`hubofhubs/terminal/strings.py` holds the English sentences under the keys of the Quest app's English pack. `tests/test_terminal_drift.py` compares them with that pack and runs the app's own `workTrace.ts` on 34 fixtures against the Python port (live line, summary, groups), when the sibling checkout, `node` and its compiler are present; otherwise it skips with the reason.
