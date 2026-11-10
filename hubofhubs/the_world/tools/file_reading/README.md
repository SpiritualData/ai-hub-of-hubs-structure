# File Reading

**Purpose:** Read the files a task or a card builder needs, without leaving the folder it was given.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > File Reading

Part of [Using the tools of the outside world](../README.md)

## File Reading (`read-files`)

- Out of scope: Writing files (File Editing does that) and deciding which files matter (Cards From Files and the Context Retriever do that).
- Delegates to: internal-context
- Entry call: `hubofhubs.run("read-files", {'root': '.', 'paths': []})`
- Selected implementation: Folder reader (`folder_reader`)
- Metric: Files read inside the folder
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 136 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Folder reader | `read-files:folder_reader` | Lists and reads the text files of one folder, never outside it, skipping what is not text or too large. | [`hubofhubs/the_world/tools/file_reading/read_files.py`](read_files.py) | selected |

## Metrics

- Files read inside the folder (`metric-read-files`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
