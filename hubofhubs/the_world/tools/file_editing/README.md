# File Editing

*ESOI records kept beside the code in `hubofhubs/the_world/tools/file_editing`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The AI uses the tool of each category the person's authority allows, and a category gains a better integration without any product rewriting its code.

These are the solutions of [Using the tools of the outside world](../README.md).

## How the solutions fit together

Tools lets the AI use the tool of a category and refuses a category the authority does not allow. Web Search brings in the live web. File Reading reads the files of a folder. File Editing changes one file by instruction. Connected System Operations calls a write operation of a connected system. Delegated Agent Sessions gives open-ended work to an agent that runs in its own session.

## File Editing (`file-editing`)

Make the file change that was asked for, and no other.

- Entry call: `hubofhubs.run("file-editing", ...)`
- Selected implementation: One-call file edit (`fast_edit`)
- Metric: Goal met by its own tests
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 122 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| One-call file edit | `file-editing:fast_edit` | [`hubofhubs/the_world/tools/file_editing/fast_edit.py`](fast_edit.py) | selected |

## Metrics

- Goal met by its own tests (`metric-file-editing`): leader `fast_edit`, 29 of 30 cases

## Problems

- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)
