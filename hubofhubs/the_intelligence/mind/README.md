# What the Mind sees and does for one request

**Vision statement:** For one request the Mind works from one view of the information, breaks the request into pieces, hands a piece on only when a worker is needed, and writes the plan, request or communication its reader needs.

Breadcrumb: [Top](../../../esoi/README.md) > [How the AI processes information](../README.md) > What the Mind sees and does for one request

This sub-intent arises as the implementation `the-mind:composition` of its parent intent [`the_intelligence`](../README.md). Opportunities: What the Mind is shown, how it breaks a request into pieces and how it writes can each be improved on its own measure, and every handoff carries the person's authority and the done-standard of its sub-goal.

## How the solutions fit together

Context Intake takes in what was prepared for a request and what the workers brought back, as one view. Planner breaks the request into pieces, each with the sub-goal it must meet. For each piece, Nervous System gives a risk signal before the piece is passed on. Judgment Calls then decides for the person whether to proceed or ask. Delegation passes each allowed piece to the worker its category names, only when a worker is needed, with the Representative's authority and the done-standard of the sub-goal. Response Writer writes the plan, request or communication from the results, to the quality profile.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Context Intake](context_intake/README.md) (solution with implementations): Give the Planner one view of what is known for a request, whatever its source.
- [Delegation](delegation/README.md) (solution with implementations): Hand work on without losing the authority it was given or the standard that says it is done, enforce the authority, the goal record's budget and cancellation (down to a running agent session), and refuse a piece it may not run with the reason.
- [Planner](planner/README.md) (solution with implementations): Turn a request into pieces that can be done and checked, each with the worker category that fits it, and replan from what failed.
- [Response Writer](response_writer/README.md) (solution with implementations): Write what the Mind outputs for its reader.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Context Intake | `context-intake` | `hubofhubs.run("context-intake", {'request': 'what is the latest Rust version?'})` | Merge into one labelled view (`one_view`) | One view with every source named |
| Delegation | `delegation` | `hubofhubs.run("delegation", {'pieces': [], 'authority': {}})` | Route to Tools and Science (`to_tools`) | Handoffs keep authority, budget and cancellation |
| Planner | `planner` | `hubofhubs.run("planner", {'request': 'what is the latest Rust version?'})` | Split and route by cues (`cue_router`) | Requests routed to the right worker |
| Response Writer | `response-writer` | `hubofhubs.run("response-writer", {'results': [], 'profile': None})` | Cited results (`cited_results`) | Responses that say what the results hold |

## Problems and ideals

**Problems**

- One prompt carries every instruction (`hprob-one-prompt-carries-every-instruction`): As standing instructions and corrections pile up, they are often all added to every task's prompt, so cost grows and quality can fall.
- Two intakes wired by hand (`hprob-mind-has-two-intakes-wired-by-hand`): What the Mind sees for a request comes from two sources, the system's internal context and the outside, and each product wires both to the Mind its own way.
- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request is often not told the authority it carries or what done means for that piece.

**Ideals**

- Only the instructions a task needs (`hideal-only-the-instructions-a-task-needs`): Each task is given the instructions that bear on it and no others, so quality holds and cost stays low as the system learns more.
- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.

## Metrics and their leaders

- One view with every source named (`metric-context-intake`)
- Handoffs keep authority, budget and cancellation (`metric-work-delegation`)
- Requests routed to the right worker (`metric-request-planner`): leader `cue_router`, 67 of 105 cases
- Responses that say what the results hold (`metric-response-writer`): leader `cited_results`, 44 of 44 cases

## Where to go next

- Parent intent: [How the AI processes information](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_intelligence/mind/context_intake](context_intake/README.md), [hubofhubs/the_intelligence/mind/delegation](delegation/README.md), [hubofhubs/the_intelligence/mind/planner](planner/README.md), [hubofhubs/the_intelligence/mind/response_writer](response_writer/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv)

---

## The full record

### Problems

- One prompt carries every instruction (`hprob-one-prompt-carries-every-instruction`): As standing instructions and corrections pile up, they are often all added to every task's prompt, so cost grows and quality can fall.
- Two intakes wired by hand (`hprob-mind-has-two-intakes-wired-by-hand`): What the Mind sees for a request comes from two sources, the system's internal context and the outside, and each product wires both to the Mind its own way.
- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request is often not told the authority it carries or what done means for that piece.

### Ideals

- Only the instructions a task needs (`hideal-only-the-instructions-a-task-needs`): Each task is given the instructions that bear on it and no others, so quality holds and cost stays low as the system learns more.
- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Context Intake | `context-intake` | Merge into one labelled view (`one_view`) | One view with every source named |
| Delegation | `delegation` | Route to Tools and Science (`to_tools`) | Handoffs keep authority, budget and cancellation |
| Planner | `planner` | Split and route by cues (`cue_router`) | Requests routed to the right worker |
| Response Writer | `response-writer` | Cited results (`cited_results`) | Responses that say what the results hold |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Merge into one labelled view | `context-intake:one_view` | [hubofhubs/the_intelligence/mind/context_intake/intake.py](context_intake/intake.py) |  |
| Route to Tools and Science | `delegation:to_tools` | [hubofhubs/the_intelligence/mind/delegation/delegation.py](delegation/delegation.py) |  |
| Split and route by cues | `planner:cue_router` | [hubofhubs/the_intelligence/mind/planner/planning.py](planner/planning.py) |  |
| One piece, no worker | `planner:one_piece` | [hubofhubs/the_intelligence/mind/planner/planning.py](planner/planning.py) |  |
| Plan by a model | `planner:model_planner` | [hubofhubs/the_intelligence/mind/planner/model_planner.py](planner/model_planner.py) |  |
| Cited results | `response-writer:cited_results` | [hubofhubs/the_intelligence/mind/response_writer/writer.py](response_writer/writer.py) |  |
| Model synthesis | `response-writer:model_synthesis` | [hubofhubs/the_intelligence/mind/response_writer/writer.py](response_writer/writer.py) |  |

### Metrics

- One view with every source named (`metric-context-intake`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Handoffs keep authority, budget and cancellation (`metric-work-delegation`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Requests routed to the right worker (`metric-request-planner`): `esoi run request_planning --impl cue_router; esoi run request_planning --impl one_piece`
- Responses that say what the results hold (`metric-response-writer`): `esoi run response_writing --impl cited_results`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
