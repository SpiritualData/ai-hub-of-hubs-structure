# Draw the hub in the stock opencode terminal

Let the open-source opencode terminal client (V2, MIT) show the hub's work, ask before a risky step, take a note while it works, stop it and resume it, over the HTTP API that client already speaks.

`ahohs opencode-server` serves the hub's session harness on the loopback interface in the subset of opencode's API the client needs. The client is a separate program, installed by you and never bundled, vendored or imported. The arm `opencode_client_session` starts the server and the client for you.

1. Install the client into a folder of your own (it is a compiled binary of about 258 MB per platform): `npm install --prefix ~/tools/opencode @opencode/cli@2.2.7`. The tested version is 2.2.7; another major version is warned about, because the client's server API is unversioned and marked experimental.
2. Name it with `AHOHS_OPENCODE_CLIENT=~/tools/opencode/node_modules/.bin/opencode` (or put it on the path).
3. Run `ahohs work --terminal opencode_client_session "your goal"`. The full-screen interface opens (the default). `--opencode-mode inline` opens `opencode mini` instead, which streams into the terminal's own scrollback; `AHOHS_OPENCODE_MODE` sets the same. When the client is missing the hub says why, with the install line, and uses the standard terminal.
4. Or run the server by hand: `ahohs opencode-server --harness stream --folder .` prints one line to start the client against it. It listens on `127.0.0.1` with a free port and a per-run password (the client's `OPENCODE_PASSWORD`); a host that is not a loopback address is refused unless `--allow-remote` is given.

Each run gets its own folder for the client: the hub's plugin, the client's settings, its own data and state, and its update check and model fetch turned off. The folder is removed when the client exits, so a run leaves nothing in your own opencode setup.

What the client shows, and the control behind it:

| In the client | In the hub |
|---|---|
| your goal as your message and the session title (cut at a word) | `RunStarted` |
| a row per step: a read is named, a command shows its text, an edit shows its diff | `Step` |
| a refused step as an error row with the reason | `Step` with state `blocked` |
| a helper as a child session and a row naming the helper and the solution it serves | `AgentStarted`, `AgentEnded` |
| a permission prompt with the preview: allow once or reject | `Waiting`, `Approve`, `Refuse` |
| the cost and tokens in the footer, the hub's own figures | `Usage` |
| a quiet row in the transcript | `Notice`, `Review` |
| the typed note, kept with the id the client gave it | `Steer`; the harness taking it up is `Step` `message-received` |
| Esc twice: what was running ends as interrupted and the session says how to resume | `Stop`, then `Finished` stopped |
| a prompt on an idle session: a resume or a follow-up of the hub session the last run ended with | the next `Harness.start` |
| the answer, one outcome line and the resume command alone on its own line, in the shared words of `present.py` | `Finished` |

The hub's plugin (`opencode_server/plugin/hub_session/tui.tsx`, TypeScript source in the package data) uses the client's own slots: `session.composer.top` (at every width: who the work serves, who the AI acts for, a spend note only once a ceiling is half used or a cost is under a cent, the metric before and after, your notes as sent and then taken up), `sidebar.content` (the same in full, above 120 columns) and `session.panel` (the structure overview, opened by `/structure`). It reads the session's metadata, which the server fills.

What the client cannot show, whatever the arm does: its own key hints say `esc interrupt`, not stop; a permission prompt does not name approve and refuse; the sidebar needs a wide terminal; the inline interface loads no plugin; the footer's cost is at cent precision and its token figure is its own; no control stops one helper. These count in the protocol-ceiling column of the presentation metric. `evaluation/terminal_presentation/opencode_external.py` runs the real client on a pseudo-terminal through pyte at the metric's sizes (set `AHOHS_OPENCODE_CLIENT`; `AHOHS_OPENCODE_PLUGIN=off` runs it without the plugin to see what the plugin changes). See `docs/explanation/working-with-the-ai-while-it-works.md` for the requirements.

## Use the client as your own program's terminal

The opencode client is the hub's selected terminal (owner decision, 2026-11-12; see the Terminal Experience record). A program that is not `ahohs` gets it through `hubofhubs.api.host_in_opencode`, never by copying the server wiring: `host_in_opencode(build, folder, person=..., command=..., tiers=..., commands=[SlashCommand(...)], header=lambda: [...])` serves the session, launches the client, waits for it and says the closing line. `build(folder, tier)` returns the program's own `Harness` (one run per message). `commands` are slash commands the client lists in its own menu (a command's `run(argument)` returns the lines to say as one quiet row; a typed `/name argument` runs the same way, even while a run works). `header` returns short lines the plugin shows beside who the work serves. `on_bridge` hands back the `Bridge`, whose `say(lines)` adds a quiet row and `select_tier(name)` moves the model picker. `opencode_available()` says why the client cannot run here, counting a client of another major version as not available, so a program can fall back to its own terminal.
