# Context Intake

*ESOI records kept beside the code in `hubofhubs/the_intelligence/mind/context_intake`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

For one request the Mind works from one view of the information, breaks the request into pieces, hands a piece on only when a worker is needed, and writes the plan, request or communication its reader needs.

These are the solutions of [What the Mind sees and does for one request](../README.md).

## How the solutions fit together

Context Intake takes in what was prepared for a request and what the workers brought back, as one view. Planner breaks the request into pieces, each with the sub-goal it must meet. For each piece, Nervous System gives a risk signal before the piece is passed on. Judgment Calls then decides for the person whether to proceed or ask. Delegation passes each allowed piece to the worker its category names, only when a worker is needed, with the Representative's authority and the done-standard of the sub-goal. Response Writer writes the plan, request or communication from the results, to the quality profile.

## Context Intake (`context-intake`)

Give the Planner one view of what is known for a request, whatever its source.

- Entry call: `hubofhubs.run("context-intake", {'request': 'what is the latest Rust version?'})`
- Selected implementation: Merge into one labelled view (`one_view`)
- Metric: One view with every source named
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../../critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../../critical_thinking/goal_completion/goal_completion.py) and 141 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Merge into one labelled view | `context-intake:one_view` | [`hubofhubs/the_intelligence/mind/context_intake/intake.py`](intake.py) | selected |

## Metrics

- One view with every source named (`metric-context-intake`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)
