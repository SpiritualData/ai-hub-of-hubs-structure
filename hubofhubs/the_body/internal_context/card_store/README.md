# Card Store

**Purpose:** Keep cards and find them again.

Breadcrumb: [Top](../../../../esoi/README.md) > [The form and internal context of a system](../../README.md) > [Internal Context](../README.md) > Card Store

Part of [Internal Context](../README.md)

## Card Store (`card-store`)

- Out of scope: Building the cards from files (Cards From Files does that) and choosing which cards a request needs (the Context Retriever does that).
- Delegates to: cards-from-files, context-retriever
- Entry call: `hubofhubs.run("card-store", 'rust release')`
- Selected implementation: Local card store (`local_card_store`)
- Metric: Cards found again, none lost
- Implemented by: [`hubofhubs/the_body/__init__.py`](../../__init__.py), [`hubofhubs/the_body/filemodes.py`](../../filemodes.py), [`hubofhubs/the_body/flow.py`](../../flow.py), [`hubofhubs/the_body/hands/__init__.py`](../../hands/__init__.py), [`hubofhubs/the_body/hands/integrations.py`](../../hands/integrations.py), [`hubofhubs/the_body/hands/interface.py`](../../hands/interface.py), [`hubofhubs/the_body/hands/tests/test_hands.py`](../../hands/tests/test_hands.py), [`hubofhubs/the_body/intake_sources/__init__.py`](../../intake_sources/__init__.py) and 64 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Local card store | `card-store:local_card_store` | Keeps the hub's cards in SQLite, in memory or in one file; search matches every word of the query as a substring. | [`hubofhubs/the_body/internal_context/card_store/cardstore.py`](cardstore.py) | selected |

## Metrics

- Cards found again, none lost (`metric-card-store`): leader `local_card_store`, 35 of 35 cases

## Where to go next

- Up: [hubofhubs/the_body/internal_context](../README.md)
- Intent: [The form and internal context of a system](../../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
