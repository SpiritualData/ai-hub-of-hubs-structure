# File Reading

*ESOI records kept beside the code in `hubofhubs/the_world/tools/file_reading`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The AI uses the tool of each category the person's authority allows, and a category gains a better integration without any product rewriting its code.

These are the solutions of [Using the tools of the outside world](../README.md).

## How the solutions fit together

Tools lets the AI use the tool of a category and refuses a category the authority does not allow. Web Search brings in the live web. File Reading reads the files of a folder. File Editing changes one file by instruction. Connected System Operations calls a write operation of a connected system. Delegated Agent Sessions gives open-ended work to an agent that runs in its own session.

## File Reading (`read-files`)

Read the files a task or a card builder needs, without leaving the folder it was given.

- Entry call: `hubofhubs.run("read-files", {'root': '.', 'paths': []})`
- Selected implementation: Folder reader (`folder_reader`)
- Metric: Files read inside the folder
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 120 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Folder reader | `read-files:folder_reader` | [`hubofhubs/the_world/tools/file_reading/read_files.py`](read_files.py) | selected |

## Metrics

- Files read inside the folder (`metric-read-files`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)
