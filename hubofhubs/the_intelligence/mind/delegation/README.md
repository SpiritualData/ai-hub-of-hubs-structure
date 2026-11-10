# Delegation

**Purpose:** Hand work on without losing the authority it was given or the standard that says it is done, enforce the authority, the goal record's budget and cancellation (down to a running agent session), and refuse a piece it may not run with the reason.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [What the Mind sees and does for one request](../README.md) > Delegation

Part of [What the Mind sees and does for one request](../README.md)

## Delegation (`delegation`)

- Out of scope: Deciding the pieces (the Planner does that), checking the done-standard (Goal Completion does that), and carrying out the work (the tools do that).
- Delegates to: planner, goal-completion, the-tools
- Entry call: `hubofhubs.run("delegation", {'pieces': [], 'authority': {}})`
- Selected implementation: Route to Tools and Science (`to_tools`)
- Metric: Handoffs keep authority, budget and cancellation
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 227 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Route to Tools and Science | `delegation:to_tools` | Hands each piece to the worker its tool names (web search, file reading or editing, connected systems, agent sessions, Science), refusing a category the authority does not allow, a piece past the budget or after a cancel, and handing a stop hook to the worker. | [`hubofhubs/the_intelligence/mind/delegation/delegation.py`](delegation.py) | selected |

## Metrics

- Handoffs keep authority, budget and cancellation (`metric-work-delegation`)

## Problems

- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request is often not told the authority it carries or what done means for that piece.

## Ideals

- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
