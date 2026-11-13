# Intuition

**Purpose:** Let useful information surface unasked.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Finding and preparing information for the Mind](../README.md) > Intuition

Part of [Finding and preparing information for the Mind](../README.md)

## Intuition (`the-intuition`)

- Out of scope: Answering a query (the Context Retriever does that).
- Delegates to: internal-context
- Entry call: `hubofhubs.run("the-intuition", {'request': 'what is the latest Rust version?'})`
- Selected implementation: What was taken for similar requests (`co_taken`)
- Metric: Unasked items are taken and useful
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 255 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Nearest items by wording | `the-intuition:nearest_cards` | TF-IDF cosine between the request and every item Internal Context can read; the closest items above a floor, best first, within the limit. | [`hubofhubs/the_intelligence/subconscious/intuition/nearest_cards.py`](nearest_cards.py) |  |
| What was taken for similar requests | `the-intuition:co_taken` | Nearest items by wording, plus the items the Mind took for similar earlier requests, each take fading with a 14-day half-life. | [`hubofhubs/the_intelligence/subconscious/intuition/co_taken.py`](co_taken.py) | selected |

## Metrics

- Unasked items are taken and useful (`metric-the-intuition`): leader `co_taken`, 20 of 20 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Finding and preparing information for the Mind](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
