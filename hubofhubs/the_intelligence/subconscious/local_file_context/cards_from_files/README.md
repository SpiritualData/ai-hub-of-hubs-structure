# Cards From Files

**Purpose:** Propose the cards a folder of files needs, in the card store record shape, for the Subconscious to keep and recall.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How the AI processes information](../../../README.md) > [Finding and preparing information for the Mind](../../README.md) > [Local File Context](../README.md) > Cards From Files

Part of [Local File Context](../README.md)

## Cards From Files (`cards-from-files`)

- Out of scope: Keeping the cards (Card Store does that) and reading or writing files in general (Read Files and File Editing do that).
- Delegates to: card-store, read-files
- Entry call: `hubofhubs.run("cards-from-files", {'root': '.', 'files': [], 'existing': {}})`
- Selected implementation: Import graph topic cards (`import_graph_topic_cards`)
- Metric: Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../../critical_thinking/decision_check/remainder.py) and 255 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Model-written topic cards | `cards-from-files:llm_topic_cards` | Walks the folder, picks representative files per area and asks a model to propose topic cards that name what people ask about, then removes duplicates. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| One card per file | `cards-from-files:per_file_symbols` | BASELINE for finding a file: one card per source file, described by its docstrings and symbols. A floor to beat on file finding, not a card builder: a card per file is an index of files and is not what a card store keeps. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| Graphify file groups | `cards-from-files:graphify_files` | Runs Graphify's code-only extraction, collapses its symbol graph to a graph of files, and makes one card per community of files. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_graphify.py`](cards_from_graphify.py) |  |
| File plus topic cards | `cards-from-files:file_plus_topic_cards` | The one-card-per-file floor plus the persisted topic cards (their ids prefixed ``topic-``): the selector can pick a file's own card or a topic card, whichever ranks higher for the task. No model is called. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| Topic cards replay | `cards-from-files:topic_cards_replay` | The topic cards of one recorded paid build of ``llm_topic_cards``, returned as recorded: a replay, not a new build. It calls no model. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| Cochange topic cards | `cards-from-files:cochange_topic_cards` | Topic cards from co-change: files changed together in at least ``min_support`` commits of a recorded history are one card (at most ``cap`` files, a file in one card); the commit subjects that changed them together are the card's topic words; files with no co-change get folder cards when ``backfill`` is true. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_topics.py`](cards_from_topics.py) |  |
| Import graph topic cards | `cards-from-files:import_graph_topic_cards` | Topic cards from the import graph: files that import each other are one card (at most ``cap`` files, a file in one card), the most connected pairs first; files that import nothing in the corpus get folder cards when ``backfill`` is true. | [`hubofhubs/the_intelligence/subconscious/local_file_context/cards_from_files/cards_from_topics.py`](cards_from_topics.py) | selected |

## Metrics

- Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size (`metric-cards-from-files`): leader `import_graph_topic_cards`, 112 of 252 cases

## Problems

- Files without cards (`hprob-files-without-cards`): A consumer whose knowledge lives in files has no cards for it until something writes them, and cards written once go stale as the files change.

## Where to go next

- Up: [hubofhubs/the_intelligence/subconscious/local_file_context](../README.md)
- Intent: [Finding and preparing information for the Mind](../../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
