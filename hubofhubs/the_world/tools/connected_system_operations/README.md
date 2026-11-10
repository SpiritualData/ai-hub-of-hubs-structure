# Connected System Operations

**Purpose:** Carry out an operation of a connected system on the AI's behalf.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > Connected System Operations

Part of [Using the tools of the outside world](../README.md)

## Connected System Operations (`connected-system-operations`)

- Out of scope: Deciding to call it (the Planner and Delegation do that), the system's enduring integrations (Hands does that) and editing files (File Editing does that).
- Delegates to: planner, delegation, the-hands, file-editing
- Entry call: `hubofhubs.run("connected-system-operations", ...)`
- Selected implementation: none selected
- Metric: The operation is carried out and nothing else
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 161 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| One-call MCP write | `connected-system-operations:mcp_operations` | Picks at most one writable operation of an MCP server and its arguments in one model call and runs it. | [`hubofhubs/the_world/tools/connected_system_operations/mcp_operations.py`](mcp_operations.py) |  |

## Metrics

- The operation is carried out and nothing else (`metric-connected-system-operations`)

## Problems

- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Most products wire each connected system's operations by hand.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
