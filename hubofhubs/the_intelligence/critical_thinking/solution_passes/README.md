# Solution Passes

**Purpose:** Make every relevant solution judge a request against its own records, at every level of the hierarchy, so durable memory and expertise are never skipped.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Solution Passes

Part of [Holding a request to a measure](../README.md)

## Solution Passes (`solution-passes`)

- Out of scope: Choosing which solutions are relevant and forming their prompts (Relevant Solutions and the Subconscious do that), turning findings into the goal's target (Metric Translation does that), checking the work (Goal Completion does that) and writing records (ESOI Application does that).
- Delegates to: model-plumbing
- Entry call: `hubofhubs.run("solution-passes", ...)`
- Selected implementation: Network passes (`network_passes`)
- Metric: Record-held answers reached and followed
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../decision_check/remainder.py) and 201 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Network passes | `solution-passes:network_passes` | One cheap pass per relevant solution in parallel on its generated prompt, then parent passes one level at a time that stop at the first scope with no effect on its children's combination, and one narrow pass per dependent; a consumer's own pass replaces the model pass for a solution it names. | [`hubofhubs/the_intelligence/critical_thinking/solution_passes/passes.py`](passes.py) | selected |

## Metrics

- Record-held answers reached and followed (`metric-solution-passes`): no result recorded

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
