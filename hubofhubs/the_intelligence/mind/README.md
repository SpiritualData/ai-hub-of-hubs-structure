# What the Mind sees and does for one request

**Vision statement:** For one request the Mind works from one view of the information, breaks the request into pieces, hands a piece on only when a worker is needed, and writes the plan, request or communication its reader needs.

Breadcrumb: [Top](../../../esoi/README.md) > [How the AI processes information](../README.md) > What the Mind sees and does for one request

This sub-intent arises as the implementation `the-mind:composition` of its parent intent [`the_intelligence`](../README.md). Opportunities: What the Mind is shown, how it breaks a request into pieces and how it writes can each be improved on its own measure, and every handoff carries the person's authority and the done-standard of its sub-goal.

## How the solutions fit together

Context Intake takes in what was prepared for a request and what the workers brought back, as one view. Planner breaks the request into pieces, each with the sub-goal it must meet. For each piece, Nervous System gives a risk signal before the piece is passed on. Judgment Calls then decides for the person whether to proceed or ask. Delegation passes each allowed piece to the worker its category names, only when a worker is needed, with the Representative's authority and the done-standard of the sub-goal. Response Writer writes the plan, request or communication from the results, to the quality profile.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["planner"]
    s1["Route a Request<br/><i>route-a-request</i>"]
    s0 -->|"The pieces of a request, each with the sub-goal it must meet"| s1
```

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Context Intake](context_intake/README.md) (solution with implementations): Give the Planner one view of what is known for a request, whatever its source.
- [Delegation](delegation/README.md) (solution with implementations): Hand work on without losing the authority it was given or the standard that says it is done, enforce the authority, the goal record's budget and cancellation (down to a running agent session), and refuse a piece it may not run with the reason.
- [Planner](planner/README.md) (solution with implementations): Turn a request into pieces that can be done and checked, each with the worker category that fits it, and replan from what failed.
- [Resolve a Reference](reference_resolver/README.md) (solution with implementations): Tie a phrase to the thing it names only when it is that thing.
- [Route a Request](request_router/README.md) (solution with implementations): Understand what a request asks for before the system answers, acts or writes, in one place.
- [Response Writer](response_writer/README.md) (solution with implementations): Write what the Mind outputs for its reader.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Context Intake | `context-intake` | `hubofhubs.run("context-intake", {'request': 'what is the latest Rust version?'})` | Merge into one labelled view (`one_view`) | One view with every source named |
| Delegation | `delegation` | `hubofhubs.run("delegation", {'pieces': [], 'authority': {}})` | Route to Tools and Science (`to_tools`) | Handoffs keep authority, budget and cancellation |
| Planner | `planner` | `hubofhubs.run("planner", {'request': 'what is the latest Rust version?'})` | Split and route by cues (`cue_router`) | Requests routed to the right worker |
| Resolve a Reference | `resolve-a-reference` | `hubofhubs.run("resolve-a-reference", ...)` | Id and exact match (`exact_match`) | References settled without a wrong match |
| Route a Request | `route-a-request` | `hubofhubs.run("route-a-request", ...)` | Always information (`majority_floor`) | Requests routed to what they ask for |
| Response Writer | `response-writer` | `hubofhubs.run("response-writer", {'results': [], 'profile': None})` | Cited results (`cited_results`) | Responses that say what the results hold |

## Problems and ideals

**Problems**

- One prompt carries every instruction (`hprob-one-prompt-carries-every-instruction`): As standing instructions and corrections pile up, they are often all added to every task's prompt, so cost grows and quality can fall.
- Two intakes wired by hand (`hprob-mind-has-two-intakes-wired-by-hand`): What the Mind sees for a request comes from two sources, the system's internal context and the outside, and each product wires both to the Mind its own way.
- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request is often not told the authority it carries or what done means for that piece.
- A reference is settled by shared words (`hprob-reference-settled-by-shared-words`): A phrase that refers to a person, a goal or a post is matched to a candidate by the words they share, in several parts that each do it their own way, and none of them can say that no candidate is meant.
- The route of a request is decided in many places (`hprob-request-route-decided-in-many-places`): What a request asks of the system (to be told something, something done, text written, or not yet understood) is decided by several parts that each read the request their own way: an analyser, the plan itself, a cue check, a draft flag and guards after the plan.

**Ideals**

- Only the instructions a task needs (`hideal-only-the-instructions-a-task-needs`): Each task is given the instructions that bear on it and no others, so quality holds and cost stays low as the system learns more.
- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.
- No match without the thing itself (`hideal-no-reference-without-the-thing-itself`): A phrase is tied to a candidate only when it is that candidate; otherwise the system says it does not know and goes on without guessing.
- A request goes where it asks (`hideal-a-request-goes-where-it-asks`): Each request is understood once, as what it asks for, and every later part works from that one reading.

## Metrics and their leaders

- One view with every source named (`metric-context-intake`)
- Handoffs keep authority, budget and cancellation (`metric-work-delegation`)
- Requests routed to the right worker (`metric-request-planner`): leader `cue_router`, 67 of 105 cases
- References settled without a wrong match (`metric-resolve-a-reference`): leader `exact_match`, 28 of 32 cases
- Requests routed to what they ask for (`metric-route-a-request`): leader `majority_floor`, 12 of 41 cases
- Responses that say what the results hold (`metric-response-writer`): leader `cited_results`, 44 of 44 cases

## Where to go next

- Parent intent: [How the AI processes information](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_intelligence/mind/context_intake](context_intake/README.md), [hubofhubs/the_intelligence/mind/delegation](delegation/README.md), [hubofhubs/the_intelligence/mind/planner](planner/README.md), [hubofhubs/the_intelligence/mind/reference_resolver](reference_resolver/README.md), [hubofhubs/the_intelligence/mind/request_router](request_router/README.md), [hubofhubs/the_intelligence/mind/response_writer](response_writer/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- One prompt carries every instruction (`hprob-one-prompt-carries-every-instruction`): As standing instructions and corrections pile up, they are often all added to every task's prompt, so cost grows and quality can fall.
- Two intakes wired by hand (`hprob-mind-has-two-intakes-wired-by-hand`): What the Mind sees for a request comes from two sources, the system's internal context and the outside, and each product wires both to the Mind its own way.
- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request is often not told the authority it carries or what done means for that piece.
- A reference is settled by shared words (`hprob-reference-settled-by-shared-words`): A phrase that refers to a person, a goal or a post is matched to a candidate by the words they share, in several parts that each do it their own way, and none of them can say that no candidate is meant.
- The route of a request is decided in many places (`hprob-request-route-decided-in-many-places`): What a request asks of the system (to be told something, something done, text written, or not yet understood) is decided by several parts that each read the request their own way: an analyser, the plan itself, a cue check, a draft flag and guards after the plan.

### Ideals

- Only the instructions a task needs (`hideal-only-the-instructions-a-task-needs`): Each task is given the instructions that bear on it and no others, so quality holds and cost stays low as the system learns more.
- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.
- No match without the thing itself (`hideal-no-reference-without-the-thing-itself`): A phrase is tied to a candidate only when it is that candidate; otherwise the system says it does not know and goes on without guessing.
- A request goes where it asks (`hideal-a-request-goes-where-it-asks`): Each request is understood once, as what it asks for, and every later part works from that one reading.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Context Intake | `context-intake` | Merge into one labelled view (`one_view`) | One view with every source named |
| Delegation | `delegation` | Route to Tools and Science (`to_tools`) | Handoffs keep authority, budget and cancellation |
| Planner | `planner` | Split and route by cues (`cue_router`) | Requests routed to the right worker |
| Resolve a Reference | `resolve-a-reference` | Id and exact match (`exact_match`) | References settled without a wrong match |
| Route a Request | `route-a-request` | Always information (`majority_floor`) | Requests routed to what they ask for |
| Response Writer | `response-writer` | Cited results (`cited_results`) | Responses that say what the results hold |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Merge into one labelled view | `context-intake:one_view` | [hubofhubs/the_intelligence/mind/context_intake/intake.py](context_intake/intake.py) |  |
| Route to Tools and Science | `delegation:to_tools` | [hubofhubs/the_intelligence/mind/delegation/delegation.py](delegation/delegation.py) |  |
| Split and route by cues | `planner:cue_router` | [hubofhubs/the_intelligence/mind/planner/planning.py](planner/planning.py) |  |
| One piece, no worker | `planner:one_piece` | [hubofhubs/the_intelligence/mind/planner/planning.py](planner/planning.py) |  |
| Plan by a model | `planner:model_planner` | [hubofhubs/the_intelligence/mind/planner/model_planner.py](planner/model_planner.py) |  |
| Id and exact match | `resolve-a-reference:exact_match` | [hubofhubs/the_intelligence/mind/reference_resolver/resolving.py](reference_resolver/resolving.py) |  |
| A model judges sameness | `resolve-a-reference:model_judged` | [hubofhubs/the_intelligence/mind/reference_resolver/resolving.py](reference_resolver/resolving.py) |  |
| Most shared words | `resolve-a-reference:shared_words` | [hubofhubs/the_intelligence/mind/reference_resolver/resolving.py](reference_resolver/resolving.py) |  |
| One cheap classifier call | `route-a-request:single_classifier` | [hubofhubs/the_intelligence/mind/request_router/routing.py](request_router/routing.py) |  |
| Route read off the plan | `route-a-request:plan_derived` | [hubofhubs/the_intelligence/mind/request_router/routing.py](request_router/routing.py) |  |
| Always information | `route-a-request:majority_floor` | [hubofhubs/the_intelligence/mind/request_router/routing.py](request_router/routing.py) |  |
| Cited results | `response-writer:cited_results` | [hubofhubs/the_intelligence/mind/response_writer/writer.py](response_writer/writer.py) |  |
| Model synthesis | `response-writer:model_synthesis` | [hubofhubs/the_intelligence/mind/response_writer/writer.py](response_writer/writer.py) |  |

### Metrics

- One view with every source named (`metric-context-intake`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Handoffs keep authority, budget and cancellation (`metric-work-delegation`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Requests routed to the right worker (`metric-request-planner`): `esoi run request_planning --impl cue_router; esoi run request_planning --impl one_piece`
- References settled without a wrong match (`metric-resolve-a-reference`): `esoi run resolve_a_reference --impl exact_match; esoi run resolve_a_reference --impl shared_words; esoi run resolve_a_reference --impl model_judged --max-calls 32`
- Requests routed to what they ask for (`metric-route-a-request`): `esoi run route_a_request --impl plan_derived; esoi run route_a_request --impl majority_floor; esoi run route_a_request --impl single_classifier --max-calls 41`
- Responses that say what the results hold (`metric-response-writer`): `esoi run response_writing --impl cited_results`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
