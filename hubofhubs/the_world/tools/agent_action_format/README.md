# Agent Action Format

**Purpose:** Execute a model's actions in the format that model is trained on, so no call is spent on a protocol it must be taught.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > Agent Action Format

Part of [Using the tools of the outside world](../README.md)

## Agent Action Format (`agent-action-format`)

- Out of scope: Choosing which model or which loop drives the work (Delegated Agent Sessions does that), running a command safely (Command Execution does that) and editing a single file by instruction (File Editing does that).
- Delegates to: command-execution, file-editing
- Entry call: `hubofhubs.run("agent-action-format", {'reply': 'READ: README.md', 'working_dir': '.'})`
- Selected implementation: Either format (`any_format`)
- Metric: Scripted actions executed as intended, per format
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/investigation_record.py`](../../learning/investigation_record.py), [`hubofhubs/the_world/learning/investigation_store.py`](../../learning/investigation_store.py), [`hubofhubs/the_world/learning/recorded_research.py`](../../learning/recorded_research.py) and 208 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Hub text protocol | `agent-action-format:text_protocol` | Reads the hub loop's protocol (RUN, READ, CHECK, search and replace edit blocks) and the function-call markup a model writes when it forgets the protocol, including markup that wraps protocol lines. | [`hubofhubs/the_world/tools/agent_action_format/arms.py`](arms.py) |  |
| Native tool calls | `agent-action-format:native_tool_calls` | Reads tool calls in the shape of Claude Code's tools (Bash, Read, Write, Edit, Glob) as a JSON list and runs each in the folder, refusing an edit whose old text is not unique and a path outside the folder. | [`hubofhubs/the_world/tools/agent_action_format/arms.py`](arms.py) |  |
| Either format | `agent-action-format:any_format` | Takes native tool calls when the reply is a JSON list of them and the text protocol otherwise, so a harness that drives several model families reads each in the format it emits. | [`hubofhubs/the_world/tools/agent_action_format/arms.py`](arms.py) | selected |
| OpenAI apply_patch and shell | `agent-action-format:apply_patch_v4a` | Reads the tool calls of OpenAI's coding agents: apply_patch (an operation with a V4A diff: create_file, update_file or delete_file; hunks located by their context, exactly and then ignoring white space) and shell (the command as an argument list), as a JSON list of calls, and runs each in the folder. | [`hubofhubs/the_world/tools/agent_action_format/arms.py`](arms.py) |  |

## Metrics

- Scripted actions executed as intended, per format (`metric-agent-action-format`): leader `any_format`, 15 of 15 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
