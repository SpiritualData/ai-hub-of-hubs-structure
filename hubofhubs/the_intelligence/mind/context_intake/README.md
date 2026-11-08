# Context Intake

**Purpose:** Give the Planner one view of what is known for a request, whatever its source.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [What the Mind sees and does for one request](../README.md) > Context Intake

Part of [What the Mind sees and does for one request](../README.md)

## Context Intake (`context-intake`)

- Out of scope: Finding or preparing the information, which is the Subconscious and the World.
- Delegates to: the-subconscious, the-world
- Entry call: `hubofhubs.run("context-intake", {'request': 'what is the latest Rust version?'})`
- Selected implementation: Merge into one labelled view (`one_view`)
- Metric: One view with every source named
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/tests/test_decision_check.py`](../../critical_thinking/decision_check/tests/test_decision_check.py) and 176 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Merge into one labelled view | `context-intake:one_view` | Merges the cards, picked file pieces and offered items the Subconscious prepared with the answer and sources the World brought into one view, each line naming where it came from. | [`hubofhubs/the_intelligence/mind/context_intake/intake.py`](intake.py) | selected |

## Metrics

- One view with every source named (`metric-context-intake`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
