# Route a Request

**Purpose:** Understand what a request asks for before the system answers, acts or writes, in one place.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [What the Mind sees and does for one request](../README.md) > Route a Request

Part of [What the Mind sees and does for one request](../README.md)

## Route a Request (`route-a-request`)

- Out of scope: Choosing the worker for each piece (the Planner does that), whether an action is allowed (Judgment Calls) and writing the reply (the Response Writer).
- Delegates to: planner, model-plumbing
- Entry call: `hubofhubs.run("route-a-request", ...)`
- Selected implementation: Always information (`majority_floor`)
- Metric: Requests routed to what they ask for
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/tests/test_decision_check.py`](../../critical_thinking/decision_check/tests/test_decision_check.py) and 176 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| One cheap classifier call | `route-a-request:single_classifier` | One model call through Model Plumbing, at the cheap tier, is asked which of information, act, draft or clarify the request is, reading the request and what the Mind can already see; a reply outside the list raises. | [`hubofhubs/the_intelligence/mind/request_router/routing.py`](routing.py) |  |
| Route read off the plan | `route-a-request:plan_derived` | The route is read off the plan the Planner already made: a plan that needs more from the person is clarify, a text deliverable is draft, a plan with a worker that changes something is act, any other plan is information. | [`hubofhubs/the_intelligence/mind/request_router/routing.py`](routing.py) |  |
| Always information | `route-a-request:majority_floor` | Says information for every request. | [`hubofhubs/the_intelligence/mind/request_router/routing.py`](routing.py) | selected |

## Metrics

- Requests routed to what they ask for (`metric-route-a-request`): leader `majority_floor`, 12 of 41 cases

## Problems

- The route of a request is decided in many places (`hprob-request-route-decided-in-many-places`): What a request asks of the system (to be told something, something done, text written, or not yet understood) is decided by several parts that each read the request their own way: an analyser, the plan itself, a cue check, a draft flag and guards after the plan.

## Ideals

- A request goes where it asks (`hideal-a-request-goes-where-it-asks`): Each request is understood once, as what it asks for, and every later part works from that one reading.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
