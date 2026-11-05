# Using the tools of the outside world

The AI uses the tool of each category the person's authority allows, and a category gains a better integration without any product rewriting its code.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-tools:composition` of its parent intent [`the_world`](../README.md). Opportunities: Each tool category is a solution and each integration an implementation, so a better search, file editor, operation caller or agent runner can replace an older one on its own measure.

## How the solutions fit together

Tools lets the AI use the tool of a category and refuses a category the authority does not allow. Web Search brings in the live web. File Reading reads the files of a folder. File Editing changes one file by instruction. Connected System Operations calls a write operation of a connected system. Delegated Agent Sessions gives open-ended work to an agent that runs in its own session.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Connected System Operations | `connected-system-operations` | `hubofhubs.run("connected-system-operations", ...)` | none selected | The operation is carried out and nothing else |
| Delegated Agent Sessions | `delegated-agent-sessions` | `hubofhubs.run("delegated-agent-sessions", ...)` | Claude Code, steerable session (`stream_json_goal_runner`) | Harness, context, sub-agents and recursion ranked, Goal met by its own tests (agent sessions) |
| File Editing | `file-editing` | `hubofhubs.run("file-editing", ...)` | One-call file edit (`fast_edit`) | Goal met by its own tests |
| File Reading | `read-files` | `hubofhubs.run("read-files", {'root': '.', 'paths': []})` | Folder reader (`folder_reader`) | Files read inside the folder |
| Web Search | `web-search` | `hubofhubs.run("web-search", 'latest Rust version')` | Gemini grounding (`gemini`) | Search finds the source |

## Problems and ideals

**Problems**

- Every product wires its own tools (`hprob-each-product-wires-its-own-tools`): Each product wires its own integrations and finds a person's data its own way, so a new kind of integration means new code and a person's data locations are asked for again by every product.
- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Most products wire each connected system's operations by hand.
- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.

## Metrics and their leaders

- Integration added with zero code (`metric-integration-added-with-zero-code`)
- Integration served by combined hubs (`metric-integration-served-by-combined-hubs`)
- Integration available within the weekly refresh (`metric-integration-availability-lag`)
- Integration credentials stay with their user (`metric-integration-credential-isolation`)
- Share of connections that need no code (`metric-connection-config-share`)
- The operation is carried out and nothing else (`metric-connected-system-operations`)
- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`)
- Goal met by its own tests (agent sessions) (`metric-delegated-agent-sessions`): leader `none`, 0 of 12 cases
- Goal met by its own tests (`metric-file-editing`): leader `fast_edit`, 29 of 30 cases
- Files read inside the folder (`metric-read-files`)
- and 1 more: all 11 are in [metrics](#metrics) of the full record below

## Where to go next

- Parent intent: [Awareness of the outside and interaction with it](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_world/tools/connected_system_operations](connected_system_operations/README.md), [hubofhubs/the_world/tools/delegated_agent_sessions](delegated_agent_sessions/README.md), [hubofhubs/the_world/tools/file_editing](file_editing/README.md), [hubofhubs/the_world/tools/file_reading](file_reading/README.md), [hubofhubs/the_world/tools/web_search](web_search/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Every product wires its own tools (`hprob-each-product-wires-its-own-tools`): Each product wires its own integrations and finds a person's data its own way, so a new kind of integration means new code and a person's data locations are asked for again by every product.
- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Most products wire each connected system's operations by hand.
- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Connected System Operations | `connected-system-operations` | none selected | The operation is carried out and nothing else |
| Delegated Agent Sessions | `delegated-agent-sessions` | Claude Code, steerable session (`stream_json_goal_runner`) | Harness, context, sub-agents and recursion ranked, Goal met by its own tests (agent sessions) |
| File Editing | `file-editing` | One-call file edit (`fast_edit`) | Goal met by its own tests |
| File Reading | `read-files` | Folder reader (`folder_reader`) | Files read inside the folder |
| Web Search | `web-search` | Gemini grounding (`gemini`) | Search finds the source |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| One-call MCP write | `connected-system-operations:mcp_operations` | [hubofhubs/the_world/tools/connected_system_operations/mcp_operations.py](connected_system_operations/mcp_operations.py) |  |
| Claude Code, one shot | `delegated-agent-sessions:subprocess_goal_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/subprocess_runner.py](delegated_agent_sessions/subprocess_runner.py) |  |
| Claude Code, steerable session | `delegated-agent-sessions:stream_json_goal_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/stream_runner.py](delegated_agent_sessions/stream_runner.py) |  |
| Agent Client Protocol runner | `delegated-agent-sessions:acp_deep_runner` | [hubofhubs/the_world/tools/delegated_agent_sessions/acp_runner.py](delegated_agent_sessions/acp_runner.py) |  |
| One-call file edit | `file-editing:fast_edit` | [hubofhubs/the_world/tools/file_editing/fast_edit.py](file_editing/fast_edit.py) |  |
| Folder reader | `read-files:folder_reader` | [hubofhubs/the_world/tools/file_reading/read_files.py](file_reading/read_files.py) |  |
| Brave Search API | `web-search:brave` | [hubofhubs/the_world/tools/web_search/backends.py](web_search/backends.py) |  |
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
- The operation is carried out and nothing else (`metric-connected-system-operations`): `none`
- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`): `python3 -m pytest tests/test_deep_session_subagents.py`
- Goal met by its own tests (agent sessions) (`metric-delegated-agent-sessions`): `esoi run agent_sessions --impl stream_json_goal_runner; esoi run agent_sessions --impl subprocess_goal_runner; esoi run agent_sessions --impl acp_deep_runner; esoi run agent_sessions --impl none`
- Goal met by its own tests (`metric-file-editing`): `esoi run file_edit_goals --impl fast_edit; esoi run file_edit_goals --impl none`
- Files read inside the folder (`metric-read-files`): `python3 -m pytest tests/test_act_read_files.py`
- Search finds the source (`metric-web-search`): `esoi run search_backend --impl gemini; esoi run search_backend --impl provider; esoi run search_backend --impl searxng; esoi run search_backend --impl brave; esoi run search_backend --impl serper; esoi run search_backend --impl tavily`
