# Command Execution

**Purpose:** Run an agent's commands in its folder without hanging, flooding its prompt or touching what the person did not hand over.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > Command Execution

Part of [Using the tools of the outside world](../README.md)

## Command Execution (`command-execution`)

- Out of scope: Deciding which command to run (the loop that drives the model does that), asking a person before a risky step (Judgment Calls does that) and calling one operation of a connected system (Connected System Operations does that).
- Entry call: `hubofhubs.run("command-execution", {'command': 'sudo true', 'working_dir': '.'})`
- Selected implementation: Bubblewrap wrapper (`bubblewrap_wrapper`)
- Metric: Commands run, refused and contained as scripted
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/investigation_record.py`](../../learning/investigation_record.py), [`hubofhubs/the_world/learning/investigation_store.py`](../../learning/investigation_store.py), [`hubofhubs/the_world/learning/recorded_research.py`](../../learning/recorded_research.py) and 209 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Refusal floor alone | `command-execution:refusal_floor` | Runs the command with bash after a floor that refuses sudo, removing the disk or home folder, git push, shutdown, a download piped into a shell and any path word that leads outside the folder. | [`hubofhubs/the_world/tools/command_execution/arms.py`](arms.py) |  |
| Bubblewrap wrapper | `command-execution:bubblewrap_wrapper` | Runs the command in a bubblewrap sandbox with the whole disk read-only, the working folder and the session scratch folder (bound at /tmp) writable, after the floor; the sandbox enforces the folder boundary so a program that opens a path itself cannot write outside. | [`hubofhubs/the_world/tools/command_execution/arms.py`](arms.py) | selected |
| Anthropic sandbox runtime (not built) | `command-execution:sandbox_runtime` | Would run the command under Anthropic's sandbox runtime, which enforces filesystem and network restrictions at the operating system level without a container (bubblewrap on Linux, sandbox-exec on macOS) with a proxy that filters network access by domain. | no code yet |  |

## Metrics

- Commands run, refused and contained as scripted (`metric-command-execution`): leader `bubblewrap_wrapper`, 11 of 11 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
