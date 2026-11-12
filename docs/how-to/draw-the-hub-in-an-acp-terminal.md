# Draw the hub in an ACP terminal client

Let an existing open-source agent terminal show the hub's work, ask before a risky step, stop it and resume it, through the Agent Client Protocol.

`ahohs acp` serves the hub's session harness as an ACP agent on standard input and output. An ACP client launches it as a subprocess and draws what it says. The client is a separate program: Toad, for example, is AGPL-3.0, so it is only ever started as its own process and is never imported, vendored or made a dependency of the hub.

1. Install the protocol library, an optional extra: `pip install 'hubofhubs[acp]'` (the official `agent-client-protocol` SDK, Apache-2.0). Without it `ahohs acp` says how to install it and exits with code 2.
2. Install a client. Toad: `uv tool install -U batrachian-toad --python 3.14` (Linux and macOS).
3. Start the client on the agent: `toad acp "ahohs acp --harness stream" .` (the last argument is the folder the work happens in). `ahohs acp` takes the options of `ahohs work` that shape a run: `--harness`, `--tier`, `--folder`, `--max-spend`, `--max-time`, `--permission`, `--solution`, `--milestone`, `--as`.
4. Or let the hub start it: `ahohs work --terminal acp_client_session`. The command is `toad acp ...` by default; set `AHOHS_ACP_CLIENT` to another client's command line (`{agent}` and `{folder}` stand for the agent command and the folder; without them both are appended). When the client or the SDK is missing the hub says why and uses the standard terminal.

What the client shows, and the control behind it:

| In the client | In the hub |
|---|---|
| a tool call per step, updated in place (read, edit and run kinds) | `Step` |
| a tool call titled with the helper and its solution | `AgentStarted`, `AgentEnded` |
| a first message and plan: the solution, the milestone, who the AI acts for, the metric before | `RunStarted` |
| a permission question with the preview; Approve or Refuse | `Waiting`, `Approve`, `Refuse` (a cancelled question refuses) |
| the client's cancel; the turn ends `cancelled` and the work is kept | `Stop` |
| `session/load`, then a prompt | `Resume` (the hub session the last run ended with) |
| the hub's `_session/steering` request (the hub's own ACP client sends it) | `Steer`; the harness taking it up is a message line |
| the closing message: outcome, report, changed files, cost, the metric after; the stop reason | `Finished` |

What the protocol cannot carry: the structure tree on request, a live gauge of spend against the ceilings (it is a line at the start and in the closing report), and stopping one helper (a client cancels only the whole turn). These count in the protocol-ceiling column of the presentation metric, not as rendering faults. See `docs/explanation/working-with-the-ai-while-it-works.md` for the requirements and `evaluation/terminal_presentation` for how the screens are judged.
