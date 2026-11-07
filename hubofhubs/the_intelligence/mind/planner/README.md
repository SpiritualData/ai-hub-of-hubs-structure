# Planner

**Purpose:** Turn a request into pieces that can be done and checked, each with the worker category that fits it, and replan from what failed.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [What the Mind sees and does for one request](../README.md) > Planner

Part of [What the Mind sees and does for one request](../README.md)

## Planner (`planner`)

- Out of scope: Doing a piece (Delegation hands it on), and setting the target of the request (Metric Translation).
- Delegates to: delegation, metric-translation
- Entry call: `hubofhubs.run("planner", {'request': 'what is the latest Rust version?'})`
- Selected implementation: Split and route by cues (`cue_router`)
- Metric: Requests routed to the right worker
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/apply.py`](../../critical_thinking/esoi_application/apply.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/tests/test_esoi_application.py`](../../critical_thinking/esoi_application/tests/test_esoi_application.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py) and 168 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Split and route by cues | `planner:cue_router` | Splits a request at numbered or bulleted steps and at "then", and routes each piece to a worker category by the words it uses (an edit verb, a literature word, a question or freshness word); on a replan it plans only the pieces that failed. | [`hubofhubs/the_intelligence/mind/planner/planning.py`](planning.py) | selected |
| One piece, no worker | `planner:one_piece` | The whole request as one piece with no worker. | [`hubofhubs/the_intelligence/mind/planner/planning.py`](planning.py) |  |
| Plan by a model | `planner:model_planner` | Asks one model call, through Model Plumbing, to break the request into pieces and name the worker category of each from a closed list, reading the request, the context view, the target, the guidance and what failed last time; a reply that is not a usable plan raises an error and is never repaired by guessing. | [`hubofhubs/the_intelligence/mind/planner/model_planner.py`](model_planner.py) |  |

## Metrics

- Requests routed to the right worker (`metric-request-planner`): leader `cue_router`, 67 of 105 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
