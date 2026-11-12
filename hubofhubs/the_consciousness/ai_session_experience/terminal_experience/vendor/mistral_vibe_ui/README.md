# Mistral Vibe terminal interface, trimmed and frozen (vendored)

Third-party code. The Textual interface of Mistral Vibe, taken at release tag `v2.26.1` from <https://github.com/mistralai/mistral-vibe>
(Apache-2.0; the tag carries no NOTICE file). The hub's terminal arm `terminal-session:adopted_session` draws its sessions on this interface so that
the presentation metric can compare an adopted screen with the project's own. The licence text is `LICENSE` in this folder and `NOTICE` at the
repository root names this folder.

## A frozen snapshot

Upstream replaced this interface with a Rust one in its version 3.0.0, so there is nothing to merge: every change is made here, by hand, and the
folder is never "updated". Each copied file opens with a docstring that names its upstream file and says what was changed (Apache-2.0 section 4(b)).
The copy was made once, files were cut with the Edit tool, and the changes are the three kinds below and nothing else.

## What was taken (and kept as upstream wrote it)

| Here | Upstream (under `vibe/`) | What it draws |
|---|---|---|
| `widgets/messages.py`, `widgets/collapsible.py`, `widgets/spinner.py`, `widgets/status_message.py`, `widgets/no_markup_static.py`, `widgets/inline_notice.py`, `widgets/compact.py` | `cli/textual_ui/widgets/` | the streamed markdown answer, the reasoning display, the user's message, errors, the spinner and the status rows |
| `widgets/tools.py`, `widgets/tool_widgets.py` | same | one row per tool call updated in place, tool groups, results, per-kind approval and result widgets |
| `widgets/diff_rendering.py` | same | the diff renderer |
| `widgets/approval_app.py`, `widgets/question_app.py`, `widgets/vim_navigation.py`, `widgets/vscode_compat.py`, `widgets/navigable_option_list.py` | same | the approval and question screens |
| `widgets/todo_status.py`, `todo_tracker.py` | same | the pinned todo or plan status |
| `widgets/subagent_transcripts.py`, `widgets/chat_input/subagent_list.py`, `windowing/history.py` | same | the sub-agent list and a sub-agent's transcript |
| `widgets/loading.py`, `widgets/braille_renderer.py`, `widgets/links.py` | same | the loading line with its status words |
| `widgets/chat_input/` (container, body, text area, completion popup and manager), `commands.py`, `history_manager.py`, `input_modes.py`, `autocompletion/` | `cli/textual_ui/widgets/chat_input/`, `cli/` | the input with history, multi-line editing and slash-command completion |
| `handlers/event_handler.py` | `cli/textual_ui/handlers/` | typed history entries in, widgets out: the one place that decides what each entry becomes |
| `chat_scroll.py` | class `ChatScroll` of `cli/textual_ui/app.py` | the transcript scroll container (moved out of the 6,700-line application module, unchanged) |
| `app.tcss` | `cli/textual_ui/app.tcss` | the stylesheet (the theme's rules) |
| `word_selection.py`, `constants.py`, `count_format.py`, `shortcut_hints.py` | `cli/textual_ui/` | word selection in the transcript and small helpers |
| `protocol/` | `app_server/` (`models`, `events`, `_effect_models`, `_model`), `utils/tool_presentation.py`, `permissions.py`, `questions.py`, `user_content.py`, `agents.py` | the typed entries the interface is driven by (pydantic models): messages, reasoning, effects with their states, approval and question callbacks |
| `text_utils.py` | `utils/text.py` | a helper of the diff renderer |
| `io_utils.py` | `utils/io.py` | NEW (not upstream text): a standard-library reader of the two functions the screen calls, in place of upstream's 270-line module that guesses encodings with a third-party library |

## What was cut

Voice, audio and the narrator; the recording indicator; authentication and provider setup; the update notifier and the "what is new" screen; editor and
IDE promos; MCP, plugin, connector and skills screens; teleport and the vibe-code project screens; the session, model, thinking, log-level and theme pickers;
rewind; the feedback bar; the proxy setup; the debug console; scheduled loops, hooks, plan-file review, model-change messages and session titles; clipboard
image paste, path paste and `@file` mention completion (and the file indexer behind it); the external editor and anything that starts a program, opens a
browser, calls the network or reads the process environment or credentials; the banner; the message queue (its place is taken by the hub's own "sent, then
taken up" row); the context-window meter, the working-folder display and the spinner text; the 6,700-line application module `app.py` (the controller that hosts the app server, its configuration and its screens); and in the app-server layer
the wire parsing, the client projection and the models of every cut feature. Where a cut left a branch with nothing to do the branch was simplified, and the
dead rules of the stylesheet were removed.

## The three kinds of change

1. **Cuts**, listed above.
2. **Imports**: absolute `vibe.*` imports are relative imports inside this folder; `vibe.observability.logging.logger` is a standard-library logger; PEP 695
   syntax (`type X = ...`, `class C[T]`) is written the older way so the files parse under the 3.11 grammar (checked with the parser's feature version, not run on 3.11:
   the arm itself needs 3.12 or later).
3. **Words**: product-branded user-visible words (the product name in a sentence, two loading phrases) are neutral; em dashes in comments are commas and colons
   (the repository forbids them); the approval screen's constructor no longer takes a configuration object (it only stored it).

## Left in place although nothing in the hub uses it

A few self-contained pieces were not cut because removing them needs more edits than they cost: the user's own `!command` output message (`BashOutputMessage`) and
the queue header message in `widgets/messages.py` (with the queue header rules of the stylesheet), `UserCommandMessage`, `WarningMessage`, `InterruptMessage`, the
windowing helpers of `windowing/history.py`, `MultiCompleter`, and a handful of small functions and models (`paused_timer`, `normalize_url`, `TurnErrorCode`, and so on).

## How it is used

Nothing here is imported when the hub package is imported. `terminal_experience/adopted_session/` (the hub's thin binding layer: an adapter from session events to
the typed entries, a small Textual application that composes these widgets, and the arm) loads it inside functions, behind the extra `adopted_ui` (textual and pydantic).
The structure rules treat a folder named `vendor` as third-party: no docstring or port rule is asked of it, and the import-boundary test lets it import only the
libraries of that extra at module level.

Size when vendored: see the line counts in `terminal_experience/implementations.csv` (the arm's record), measured after the cuts.
