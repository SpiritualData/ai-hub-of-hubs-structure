# Delegation

*ESOI records kept beside the code in `hubofhubs/the_intelligence/mind/delegation`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

For one request the Mind works from one view of the information, breaks the request into pieces, hands a piece on only when a worker is needed, and writes the plan, request or communication its reader needs.

These are the solutions of [What the Mind sees and does for one request](../README.md).

## How the solutions fit together

Context Intake takes in what was prepared for a request and what the workers brought back, as one view. Planner breaks the request into pieces, each with the sub-goal it must meet. For each piece, Nervous System gives a risk signal before the piece is passed on. Judgment Calls then decides for the person whether to proceed or ask. Delegation passes each allowed piece to the worker its category names, only when a worker is needed, with the Representative's authority and the done-standard of the sub-goal. Response Writer writes the plan, request or communication from the results, to the quality profile.

## Delegation (`delegation`)

Hand work on without losing the authority it was given or the standard that says it is done, enforce the authority, the goal record's budget and cancellation (down to a running agent session), and refuse a piece it may not run with the reason.

- Entry call: `hubofhubs.run("delegation", {'pieces': [], 'authority': {}})`
- Selected implementation: Route to Tools and Science (`to_tools`)
- Metric: Handoffs keep authority, budget and cancellation
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../../critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../../critical_thinking/goal_completion/goal_completion.py) and 137 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Route to Tools and Science | `delegation:to_tools` | [`hubofhubs/the_intelligence/mind/delegation/delegation.py`](delegation.py) | selected |

## Metrics

- Handoffs keep authority, budget and cancellation (`metric-work-delegation`)

## Problems

- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request does not know the authority it carries or what done means for that piece.

## Ideals

- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)
