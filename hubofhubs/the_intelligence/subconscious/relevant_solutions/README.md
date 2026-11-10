# Relevant Solutions

**Purpose:** Find, for any request, every solution of the consumer's records that deserves its own consideration, so none is skipped.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Finding and preparing information for the Mind](../README.md) > Relevant Solutions

Part of [Finding and preparing information for the Mind](../README.md)

## Relevant Solutions (`relevant-solutions`)

- Out of scope: Forming each solution's prompt and picking its knowledge (the Subconscious composition does that with Cards From Files and Context Retriever), judging the request against a solution (Solution Passes does that) and ranking cards for an answer (Context Retriever does that).
- Entry call: `hubofhubs.run("relevant-solutions", ...)`
- Selected implementation: Records index (`records_index`)
- Metric: Solutions needing consideration named, recall first
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 223 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Records index | `relevant-solutions:records_index` | The esoi library's classifier over the consumer's specification index (lexical hits plus the records each hit links to), each solution with its chain of parents and its dependents from the records' own edges. | [`hubofhubs/the_intelligence/subconscious/relevant_solutions/records_index.py`](records_index.py) | selected |
| Records index, then a cheap model | `relevant-solutions:records_then_model` | The library's lexical arm gives three times as many candidate solutions as asked for, and one cheap model call through Model Plumbing picks among them from each candidate's name and purpose; each pick then gets its chain of parents and its dependents. | [`hubofhubs/the_intelligence/subconscious/relevant_solutions/records_then_model.py`](records_then_model.py) |  |

## Metrics

- Solutions needing consideration named, recall first (`metric-relevant-solutions`): leader `records_index`, 49 of 62 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Finding and preparing information for the Mind](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
