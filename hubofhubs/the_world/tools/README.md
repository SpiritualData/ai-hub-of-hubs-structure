# Using the tools of the outside world

**Vision statement:** The AI uses the tool of each category the person's authority allows, and a category gains a better integration without any product rewriting its code.

Breadcrumb: [Top](../../../esoi/README.md) > [Awareness of the outside and interaction with it](../README.md) > Using the tools of the outside world

This sub-intent arises as the implementation `the-tools:composition` of its parent intent [`the_world`](../README.md). Opportunities: Each tool category is a solution and each integration an implementation, so a better search, file editor, operation caller or agent runner can replace an older one on its own measure.

## How the solutions fit together

Tools lets the AI use the tool of a category and refuses a category the authority does not allow. Web Search brings in the live web. File Reading reads the files of a folder. File Editing changes one file by instruction. Connected System Operations calls a write operation of a connected system. Delegated Agent Sessions gives open-ended work to an agent that runs in its own session. Command Execution runs one shell command in a folder, bounded in time and output, refusing what must not run unattended and, where a sandbox exists, containing writes to the folder; the agent runners that execute a model's commands use it. Agent Action Format reads a model's reply in the format that model is trained on (a provider's native tool calls or the hub's text protocol) and runs each action in the folder; the loops that own their turn taking use it, and Delegated Agent Sessions is where the harnesses that do both are compared.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Agent Action Format](agent_action_format/README.md) (solution with implementations): Execute a model's actions in the format that model is trained on, so no call is spent on a protocol it must be taught.
- [Command Execution](command_execution/README.md) (solution with implementations): Run an agent's commands in its folder without hanging, flooding its prompt or touching what the person did not hand over.
- [Connected System Operations](connected_system_operations/README.md) (solution with implementations): Carry out an operation of a connected system on the AI's behalf.
- [Delegated Agent Sessions](delegated_agent_sessions/README.md) (solution with implementations): Get open-ended work done by an agent in its own session.
- [File Editing](file_editing/README.md) (solution with implementations): Make the file change that was asked for, and no other.
- [File Reading](file_reading/README.md) (solution with implementations): Read the files a task or a card builder needs, without leaving the folder it was given.
- [Web Search](web_search/README.md) (solution with implementations): Run one web search and return its hits with their sources.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Agent Action Format | `agent-action-format` | `hubofhubs.run("agent-action-format", {'reply': 'READ: README.md', 'working_dir': '.'})` | Either format (`any_format`) | Scripted actions executed as intended, per format |
| Command Execution | `command-execution` | `hubofhubs.run("command-execution", {'command': 'sudo true', 'working_dir': '.'})` | Bubblewrap wrapper (`bubblewrap_wrapper`) | Commands run, refused and contained as scripted |
| Connected System Operations | `connected-system-operations` | `hubofhubs.run("connected-system-operations", ...)` | none selected | The operation is carried out and nothing else |
| Delegated Agent Sessions | `delegated-agent-sessions` | `hubofhubs.run("delegated-agent-sessions", ...)` | `stream_json_goal_runner@provider=anthropic,tier=fast` | Harness, context, sub-agents and recursion ranked, Open-ended work finished per cost and time (agent sessions), Hard deep work finished per cost and time (agent sessions), A run finds what it needs instead of asking |
| File Editing | `file-editing` | `hubofhubs.run("file-editing", ...)` | One-call file edit (`fast_edit`) | Goal met by its own tests |
| File Reading | `read-files` | `hubofhubs.run("read-files", {'root': '.', 'paths': []})` | Folder reader (`folder_reader`) | Files read inside the folder |
| Web Search | `web-search` | `hubofhubs.run("web-search", 'latest Rust version')` | Gemini grounding (`gemini`) | Search finds the source |

## Problems and ideals

**Problems**

- Every product wires its own tools (`hprob-each-product-wires-its-own-tools`): Each product wires its own integrations and finds a person's data its own way, so a new kind of integration means new code and a person's data locations are asked for again by every product.
- A run changes what it should not or leaks a secret into a prompt (`hprob-run-changes-what-it-should-not`): A deep run, left unattended, writes or deletes outside the files its goal named, or reads a key or private file and carries it into a prompt, a reply or a file.
- A run reports success it did not reach (`hprob-run-reports-success-falsely`): A run says the goal is met when a step failed, a figure is made up, a file it names does not exist, or only part of the work was done.
- A run spends without bound or loops (`hprob-run-spends-without-bound-or-loops`): A run repeats a failing command, circles between two steps or keeps calling the model until the budget or the wall clock ends it.
- A run acts on instructions found in content it read (`hprob-run-obeys-instructions-in-what-it-reads`): A web page, a file or a command output holds text that tells the agent to do something, and the run does it.
- A run asks the person for what it could find (`hprob-run-asks-when-it-could-look`): A run raises a question or a decision for a fact it could have found itself, for example a date in a file's history, a rate in a database table or a figure on the web.
- An agent's commands hang, flood its prompt or lose their files (`hprob-commands-hang-flood-or-lose-files`): A command an agent runs never ends, prints more than the prompt can hold, is refused for a harmless reason, or leaves files in a temporary folder that the next command no longer sees.
- A model is made to write its actions in a format it is not trained on (`hprob-model-writes-in-a-format-it-is-not-trained-on`): A harness asks a model for its actions in a private text protocol, so the model spends calls on the protocol, sometimes writes its trained markup instead (which the parser ignores) and behaves less resourcefully than in its provider's own tool loop.
- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Most products wire each connected system's operations by hand.
- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.

## Metrics and their leaders

- Integration added with zero code (`metric-integration-added-with-zero-code`)
- Integration served by combined hubs (`metric-integration-served-by-combined-hubs`)
- Integration available within the weekly refresh (`metric-integration-availability-lag`)
- Integration credentials stay with their user (`metric-integration-credential-isolation`)
- Share of connections that need no code (`metric-connection-config-share`)
- Scripted actions executed as intended, per format (`metric-agent-action-format`): leader `any_format`, 15 of 15 cases
- Commands run, refused and contained as scripted (`metric-command-execution`): leader `bubblewrap_wrapper`, 11 of 11 cases
- The operation is carried out and nothing else (`metric-connected-system-operations`)
- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`)
- Open-ended work finished per cost and time (agent sessions) (`metric-delegated-agent-sessions`): leader `native_tool_calling_loop_runner@provider=anthropic,tier=fast`, 18 of 18 cases
- and 5 more: all 15 are in [metrics](#metrics) of the full record below

## Where to go next

- Parent intent: [Awareness of the outside and interaction with it](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_world/tools/agent_action_format](agent_action_format/README.md), [hubofhubs/the_world/tools/command_execution](command_execution/README.md), [hubofhubs/the_world/tools/connected_system_operations](connected_system_operations/README.md), [hubofhubs/the_world/tools/delegated_agent_sessions](delegated_agent_sessions/README.md), [hubofhubs/the_world/tools/file_editing](file_editing/README.md), [hubofhubs/the_world/tools/file_reading](file_reading/README.md), [hubofhubs/the_world/tools/web_search](web_search/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Every product wires its own tools (`hprob-each-product-wires-its-own-tools`): Each product wires its own integrations and finds a person's data its own way, so a new kind of integration means new code and a person's data locations are asked for again by every product.
- A run changes what it should not or leaks a secret into a prompt (`hprob-run-changes-what-it-should-not`): A deep run, left unattended, writes or deletes outside the files its goal named, or reads a key or private file and carries it into a prompt, a reply or a file.
- A run reports success it did not reach (`hprob-run-reports-success-falsely`): A run says the goal is met when a step failed, a figure is made up, a file it names does not exist, or only part of the work was done.
- A run spends without bound or loops (`hprob-run-spends-without-bound-or-loops`): A run repeats a failing command, circles between two steps or keeps calling the model until the budget or the wall clock ends it.
- A run acts on instructions found in content it read (`hprob-run-obeys-instructions-in-what-it-reads`): A web page, a file or a command output holds text that tells the agent to do something, and the run does it.
- A run asks the person for what it could find (`hprob-run-asks-when-it-could-look`): A run raises a question or a decision for a fact it could have found itself, for example a date in a file's history, a rate in a database table or a figure on the web.
- An agent's commands hang, flood its prompt or lose their files (`hprob-commands-hang-flood-or-lose-files`): A command an agent runs never ends, prints more than the prompt can hold, is refused for a harmless reason, or leaves files in a temporary folder that the next command no longer sees.
- A model is made to write its actions in a format it is not trained on (`hprob-model-writes-in-a-format-it-is-not-trained-on`): A harness asks a model for its actions in a private text protocol, so the model spends calls on the protocol, sometimes writes its trained markup instead (which the parser ignores) and behaves less resourcefully than in its provider's own tool loop.
- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Most products wire each connected system's operations by hand.
- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Agent Action Format | `agent-action-format` | Either format (`any_format`) | Scripted actions executed as intended, per format |
| Command Execution | `command-execution` | Bubblewrap wrapper (`bubblewrap_wrapper`) | Commands run, refused and contained as scripted |
| Connected System Operations | `connected-system-operations` | none selected | The operation is carried out and nothing else |
| Delegated Agent Sessions | `delegated-agent-sessions` | `stream_json_goal_runner@provider=anthropic,tier=fast` | Harness, context, sub-agents and recursion ranked, Open-ended work finished per cost and time (agent sessions), Hard deep work finished per cost and time (agent sessions), A run finds what it needs instead of asking |
| File Editing | `file-editing` | One-call file edit (`fast_edit`) | Goal met by its own tests |
| File Reading | `read-files` | Folder reader (`folder_reader`) | Files read inside the folder |
| Web Search | `web-search` | Gemini grounding (`gemini`) | Search finds the source |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Hub text protocol | `agent-action-format:text_protocol` | [hubofhubs/the_world/tools/agent_action_format/arms.py](agent_action_format/arms.py) |  |
| Native tool calls | `agent-action-format:native_tool_calls` | [hubofhubs/the_world/tools/agent_action_format/arms.py](agent_action_format/arms.py) |  |
| Either format | `agent-action-format:any_format` | [hubofhubs/the_world/tools/agent_action_format/arms.py](agent_action_format/arms.py) |  |
| OpenAI apply_patch and shell | `agent-action-format:apply_patch_v4a` | [hubofhubs/the_world/tools/agent_action_format/arms.py](agent_action_format/arms.py) |  |
| Refusal floor alone | `command-execution:refusal_floor` | [hubofhubs/the_world/tools/command_execution/arms.py](command_execution/arms.py) |  |
| Bubblewrap wrapper | `command-execution:bubblewrap_wrapper` | [hubofhubs/the_world/tools/command_execution/arms.py](command_execution/arms.py) |  |
| Anthropic sandbox runtime (not built) | `command-execution:sandbox_runtime` |  |  |
| One-call MCP write | `connected-system-operations:mcp_operations` | [hubofhubs/the_world/tools/connected_system_operations/mcp_operations.py](connected_system_operations/mcp_operations.py) |  |
| Claude Code, one shot | `delegated-agent-sessions:subprocess_goal_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/subprocess_runner.py](delegated_agent_sessions/subprocess_runner.py) |  |
| Claude Code, steerable session | `delegated-agent-sessions:stream_json_goal_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/stream_runner.py](delegated_agent_sessions/stream_runner.py) |  |
| Agent Client Protocol runner | `delegated-agent-sessions:acp_deep_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/acp_runner.py](delegated_agent_sessions/acp_runner.py) |  |
| Codex CLI, one shot | `delegated-agent-sessions:codex_cli_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/headless_runner.py](delegated_agent_sessions/headless_runner.py) |  |
| opencode, one shot | `delegated-agent-sessions:opencode_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/headless_runner.py](delegated_agent_sessions/headless_runner.py) |  |
| Hub's own tool loop | `delegated-agent-sessions:solution_loop_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/solution_loop_runner.py](delegated_agent_sessions/solution_loop_runner.py) |  |
| Hub's frame on the model's own tool loop | `delegated-agent-sessions:native_tool_loop_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/native_runner.py](delegated_agent_sessions/native_runner.py) |  |
| Hub's own loop on native tool calling | `delegated-agent-sessions:native_tool_calling_loop_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/tool_loop_runner.py](delegated_agent_sessions/tool_loop_runner.py) |  |
| opencode in the hub's wrapper | `delegated-agent-sessions:opencode_hub_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/framed_headless.py](delegated_agent_sessions/framed_headless.py) |  |
| One-call file edit | `file-editing:fast_edit` | [hubofhubs/the_world/tools/file_editing/fast_edit.py](file_editing/fast_edit.py) |  |
| Folder reader | `read-files:folder_reader` | [hubofhubs/the_world/tools/file_reading/read_files.py](file_reading/read_files.py) |  |
| Brave Search API | `web-search:brave` | [hubofhubs/the_world/tools/web_search/backends.py](web_search/backends.py) |  |
| Claude Code login search | `web-search:claude_login` | [hubofhubs/the_world/tools/web_search/claude_login.py](web_search/claude_login.py) |  |
| Gemini grounding | `web-search:gemini` | [hubofhubs/the_world/tools/web_search/gemini.py](web_search/gemini.py) |  |
| Provider-native search | `web-search:provider` | [hubofhubs/the_world/tools/web_search/backends.py](web_search/backends.py) |  |
| SearXNG metasearch | `web-search:searxng` | [hubofhubs/the_world/tools/web_search/backends.py](web_search/backends.py) |  |
| Serper Google search | `web-search:serper` | [hubofhubs/the_world/tools/web_search/backends.py](web_search/backends.py) |  |
| Tavily search API | `web-search:tavily` | [hubofhubs/the_world/tools/web_search/backends.py](web_search/backends.py) |  |

### Metrics

- Integration added with zero code (`metric-integration-added-with-zero-code`): `none`
- Integration served by combined hubs (`metric-integration-served-by-combined-hubs`): `none`
- Integration available within the weekly refresh (`metric-integration-availability-lag`): `none`
- Integration credentials stay with their user (`metric-integration-credential-isolation`): `none`
- Share of connections that need no code (`metric-connection-config-share`): `python3 -m pytest tests/test_registry.py tests/test_areas.py`
- Scripted actions executed as intended, per format (`metric-agent-action-format`): `esoi run agent_action_format --impl text_protocol; esoi run agent_action_format --impl native_tool_calls; esoi run agent_action_format --impl any_format`
- Commands run, refused and contained as scripted (`metric-command-execution`): `esoi run command_execution --impl refusal_floor; esoi run command_execution --impl bubblewrap_wrapper`
- The operation is carried out and nothing else (`metric-connected-system-operations`): `none`
- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`): `python3 -m pytest hubofhubs/the_world/tools/delegated_agent_sessions/tests/test_deep_session_subagents.py`
- Open-ended work finished per cost and time (agent sessions) (`metric-delegated-agent-sessions`): `esoi run agent_sessions --impl none; esoi run agent_sessions --impl stream_json_goal_runner@provider=anthropic,tier=fast; esoi run agent_sessions --impl subprocess_goal_runner@provider=anthropic,tier=fast; esoi run agent_sessions --impl subprocess_goal_runner@provider=anthropic,tier=balanced; esoi run agent_sessions --impl subprocess_goal_runner@provider=anthropic,tier=best; esoi run agent_sessions --impl opencode_runner@provider=gemini,tier=fast; esoi run agent_sessions --impl opencode_runner@provider=gemini,tier=balanced; esoi run agent_sessions --impl opencode_runner@provider=openai,tier=fast; esoi run agent_sessions --impl opencode_runner@provider=anthropic,tier=fast; esoi run agent_sessions --impl opencode_runner@provider=deepseek,tier=fast; esoi run agent_sessions --impl codex_cli_runner@provider=openai,tier=fast; esoi run agent_sessions --impl acp_deep_runner@provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl subprocess_goal_runner@provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl subprocess_goal_runner@provider=anthropic,tier=balanced; esoi run agent_sessions_hard --impl subprocess_goal_runner@provider=anthropic,tier=best; esoi run agent_sessions_hard --impl stream_json_goal_runner@provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl stream_json_goal_runner@instructions=ponytail,provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl stream_json_goal_runner@instructions=karpathy,provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl opencode_runner@provider=gemini,tier=balanced`
- Hard deep work finished per cost and time (agent sessions) (`metric-delegated-agent-sessions-hard`): `esoi run agent_sessions_hard --impl none; esoi run agent_sessions_hard --impl subprocess_goal_runner@provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl subprocess_goal_runner@provider=anthropic,tier=balanced; esoi run agent_sessions_hard --impl subprocess_goal_runner@provider=anthropic,tier=best; esoi run agent_sessions_hard --impl stream_json_goal_runner@provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl stream_json_goal_runner@instructions=ponytail,provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl stream_json_goal_runner@instructions=karpathy,provider=anthropic,tier=fast; esoi run agent_sessions_hard --impl opencode_runner@provider=gemini,tier=balanced`
- A run finds what it needs instead of asking (`metric-agent-resourcefulness`): `python3 -m pytest hubofhubs/the_world/tools/delegated_agent_sessions/tests/test_resourcefulness_surface.py`
- Goal met by its own tests (`metric-file-editing`): `esoi run file_edit_goals --impl fast_edit; esoi run file_edit_goals --impl none`
- Files read inside the folder (`metric-read-files`): `python3 -m pytest hubofhubs/the_world/tools/file_reading/tests/test_act_read_files.py`
- Search finds the source (`metric-web-search`): `esoi run search_backend --impl gemini; esoi run search_backend --impl provider; esoi run search_backend --impl searxng; esoi run search_backend --impl brave; esoi run search_backend --impl serper; esoi run search_backend --impl tavily`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
