# Structure in conversation

**Purpose:** Give a person grounded clarity in a conversation by building the reply on the structure of their intent, and stay out of the way when a turn needs none.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Structure in conversation

Part of [Holding a request to a measure](../README.md)

## Structure in conversation (`structure-in-conversation`)

- Out of scope: Classifying the turn into a move (the planner does that), writing the reply (the Response Writer does that), applying an accepted offer (ESOI Application does that) and finding which solutions a request concerns (Relevant Solutions does that).
- Delegates to: esoi-application, relevant-solutions
- Entry call: `hubofhubs.run("structure-in-conversation", {'turn': {'move': 'none'}})`
- Selected implementation: Structure move (`structure_move`)
- Metric: Replies make the structure move their turn calls for
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../decision_check/remainder.py) and 243 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| No structure | `structure-in-conversation:none` | Makes no structure move whatever the turn: no block, no offer. The reply is the general answer alone. | [`hubofhubs/the_intelligence/critical_thinking/structure_in_conversation/moves.py`](moves.py) |  |
| Structure move | `structure-in-conversation:structure_move` | Builds the block the move calls for from the records first and the caller's draft for what is missing, and at most one offer that keeps the missing pieces as ensure-one additions; a plain move leaves the reply plain. | [`hubofhubs/the_intelligence/critical_thinking/structure_in_conversation/moves.py`](moves.py) | selected |

## Metrics

- Replies make the structure move their turn calls for (`metric-structure-in-conversation`): leader `structure_move`, 36 of 36 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
