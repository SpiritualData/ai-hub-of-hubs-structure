# Cards From Files

*ESOI records kept beside the code in `hubofhubs/the_intelligence/subconscious/cards_from_files`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The information a request needs is found and prepared before the Mind asks for it, from the system's own cards, its files and what comes to mind unasked.

These are the solutions of [Finding and preparing information for the Mind](../README.md).

## How the solutions fit together

This part finds and prepares information before it is asked for. Cards From Files builds cards from the files of the system. Context Retriever picks the cards and file units that bear on the request. Intuition offers what occurs to the system unasked.

## Cards From Files (`cards-from-files`)

Propose the cards a folder of files needs, in the card store record shape, for the Subconscious to keep and recall.

- Entry call: `hubofhubs.run("cards-from-files", {'root': '.', 'files': [], 'existing': {}})`
- Selected implementation: Import graph topic cards (`import_graph_topic_cards`)
- Metric: Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../../critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../../critical_thinking/goal_completion/goal_completion.py) and 141 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Model-written topic cards | `cards-from-files:llm_topic_cards` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| One card per file | `cards-from-files:per_file_symbols` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| Graphify file groups | `cards-from-files:graphify_files` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_graphify.py`](cards_from_graphify.py) |  |
| File plus topic cards | `cards-from-files:file_plus_topic_cards` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| Topic cards replay | `cards-from-files:topic_cards_replay` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_files.py`](cards_from_files.py) |  |
| Cochange topic cards | `cards-from-files:cochange_topic_cards` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_topics.py`](cards_from_topics.py) |  |
| Import graph topic cards | `cards-from-files:import_graph_topic_cards` | [`hubofhubs/the_intelligence/subconscious/cards_from_files/cards_from_topics.py`](cards_from_topics.py) | selected |

## Metrics

- Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size (`metric-cards-from-files`): leader `import_graph_topic_cards`, 112 of 252 cases

## Problems

- Files without cards (`hprob-files-without-cards`): A consumer whose knowledge lives in files has no cards for it until something writes them, and cards written once go stale as the files change.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Finding and preparing information for the Mind](../README.md)
- Repository: [top README](../../../../README.md)
