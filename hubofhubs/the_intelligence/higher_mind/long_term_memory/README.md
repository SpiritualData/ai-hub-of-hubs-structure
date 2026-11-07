# Long-Term Memory

**Purpose:** Let the AI keep and recall what happened across requests.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [The long view across requests](../README.md) > Long-Term Memory

Part of [The long view across requests](../README.md)

## Long-Term Memory (`long-term-memory`)

- Out of scope: Where the data is stored (Internal Context declares that) and finding information for one request (Subconscious does that).
- Delegates to: internal-context, the-subconscious
- Entry call: `hubofhubs.run("long-term-memory", {'query': 'rust release', 'person': ''})`
- Selected implementation: File recall (`file_recall`)
- Metric: A later request uses what an earlier one learned
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](../../critical_thinking/esoi_application/apply.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/tests/test_esoi_application.py`](../../critical_thinking/esoi_application/tests/test_esoi_application.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py) and 168 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| File recall | `long-term-memory:file_recall` | One JSON file per person, a retention period after which items are dropped, and recall by the share of the request's keywords an item contains, damped by age with the newer ahead on a tie; an item that shares no keyword is not recalled. | [`hubofhubs/the_intelligence/higher_mind/long_term_memory/recall.py`](recall.py) | selected |
| Card Store recall | `long-term-memory:card_store_recall` | Items kept as cards in the Card Store (the person as the tag, the time as the source) and found with the store's own search one keyword at a time, ranked and aged like File recall. | [`hubofhubs/the_intelligence/higher_mind/long_term_memory/recall.py`](recall.py) |  |
| Recent window | `long-term-memory:recent_window` | The person's newest retained items whatever the request says, as a chat history window gives. | [`hubofhubs/the_intelligence/higher_mind/long_term_memory/recall.py`](recall.py) |  |

## Metrics

- A later request uses what an earlier one learned (`metric-long-term-memory`): leader `file_recall`, 16 of 17 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [The long view across requests](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
