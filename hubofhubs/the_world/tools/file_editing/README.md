# File Editing

**Purpose:** Make the file change that was asked for, and no other.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > File Editing

Part of [Using the tools of the outside world](../README.md)

## File Editing (`file-editing`)

- Out of scope: Deciding what to change (the Planner does that), checking the goal (Goal Completion does that) and running open-ended agent work (Delegated Agent Sessions does that).
- Delegates to: planner, goal-completion, delegated-agent-sessions
- Entry call: `hubofhubs.run("file-editing", ...)`
- Selected implementation: One-call file edit (`fast_edit`)
- Metric: Goal met by its own tests
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/investigation_record.py`](../../learning/investigation_record.py), [`hubofhubs/the_world/learning/investigation_store.py`](../../learning/investigation_store.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py) and 196 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| One-call file edit | `file-editing:fast_edit` | Lands a bounded file edit in one model call, using the context already gathered. | [`hubofhubs/the_world/tools/file_editing/fast_edit.py`](fast_edit.py) | selected |

## Metrics

- Goal met by its own tests (`metric-file-editing`): leader `fast_edit`, 29 of 30 cases

## Problems

- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
