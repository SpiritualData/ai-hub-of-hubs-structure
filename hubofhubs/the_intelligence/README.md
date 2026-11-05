# Processing information for one request

One request is answered from what the AI can see for it: the long view is read, the request becomes a target, the information is found and prepared, the response is planned and written, and the result is checked for goal completion and response quality.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-intelligence:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: Long-term memory, objectives and guidance, and what comes to mind unasked, are opportunities beyond the parts that answer one request. Turning a request into a measured target, and judging quality against a profile, can each be improved without changing how a single request is answered.

## How the solutions fit together

Intelligence turns one request into a response. Higher Mind keeps the long view through Long-Term Memory, Objectives and Planner Guidance, which gives an infrequent longer-term nudge. Critical Thinking turns the request into a target with a budget through Metric Translation, records it through ESOI Application, and holds the result to it through Goal Completion and Response Quality. Subconscious finds and prepares information through Cards From Files, Context Retriever and Intuition. Mind takes the request in through Context Intake, breaks it into pieces through Request Planner, passes each piece to a worker through Work Delegation and writes the response through Response Writer. Mind asks for a signal before a risky piece from Nervous System, and for the decision for the person from Judgment Calls. An unmet goal sends the flow back to the planning step within the request's budget, and when the budget or the authority runs out the flow goes to Judgment Calls. Proactivity says what is due without being asked.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Nervous System<br/><i>nervous-system</i>"]
    s1["Critical Thinking<br/><i>critical-thinking</i>"]
    s2["Subconscious<br/><i>the-subconscious</i>"]
    s3["Context Retriever<br/><i>context-retriever</i>"]
    s4["Mind<br/><i>the-mind</i>"]
    s5["Higher Mind<br/><i>higher-mind</i>"]
    s6["Long-Term Memory<br/><i>long-term-memory</i>"]
    s7["Objectives<br/><i>live-objectives</i>"]
    s8["Intuition<br/><i>the-intuition</i>"]
    s9["Context Intake<br/><i>context-intake</i>"]
    s10["Request Planner<br/><i>request-planner</i>"]
    s11["Work Delegation<br/><i>work-delegation</i>"]
    s12["Response Writer<br/><i>response-writer</i>"]
    s13["Planner Guidance<br/><i>planner-guidance</i>"]
    s14["ESOI Application<br/><i>esoi-application</i>"]
    s15["Metric Translation<br/><i>metric-translation</i>"]
    s16["Goal Completion<br/><i>goal-completion</i>"]
    s17["Response Quality<br/><i>response-quality</i>"]
    s18["Cards From Files<br/><i>cards-from-files</i>"]
    s0 -->|"One signal: proceed, redirect, answer_now, escalate_deep or..."| s4
    s3 -->|"Hits: unit id, file, first line, score, tokens and text..."| s2
    s6 -->|"Remembered events that bear on a request"| s5
    s7 -->|"The objectives in progress, their hierarchy and their state"| s5
    s8 -->|"Items offered to the Mind for a request"| s2
    s9 -->|"One view of the information for a request"| s4
    s10 -->|"The pieces of a request, each with the sub-goal it must..."| s4
    s11 -->|"The result of a piece, from the worker that did it"| s4
    s12 -->|"The written plan, request or communication"| s4
    s13 -->|"A nudge for the Planner, or nothing when none is due, and..."| s5
    s14 -->|"Edited specs and metrics, and a run of the improvement loop"| s1
    s15 -->|"A metric with a target value or improvement for a request..."| s1
    s16 -->|"Whether the goal was met, with the reason"| s1
    s17 -->|"The findings against each criterion of the profile; an..."| s1
    s18 -->|"Cards in the card-store record shape (grouping, summary..."| s2
```

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Nervous System | `nervous-system` | `hubofhubs.run("nervous-system", 'delete the old backup folder')` | Consent gate (`consent_gate`) | Risky steps stopped, ordinary steps let through, Guard marginal value |
| Critical Thinking | `critical-thinking` | `hubofhubs.run("critical-thinking", {'request': 'what is the latest Rust release?'})` | Target, goal and quality in order (`composition`) | Requests with a named problem, ideal and metric |
| Subconscious | `the-subconscious` | `hubofhubs.run("the-subconscious", 'rust release')` | Cards drawn by relevance from a store (`card_recall`) | Right context admitted, none from another scope |
| Context Retriever | `context-retriever` | `hubofhubs.run("context-retriever", ...)` | BM25 over chunk text (`bm25_body`) | Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources |
| Mind | `the-mind` | `hubofhubs.run("the-mind", {'request': 'what is the latest Rust release?'})` | The four parts of the Mind in order (`composition`) | Answer quality per dollar and per second |
| Higher Mind | `higher-mind` | `hubofhubs.run("higher-mind", {'request': 'what is the latest Rust release?'})` | Objectives, memory and guidance for one request (`composition`) | The long view survives between requests |
| Long-Term Memory | `long-term-memory` | `hubofhubs.run("long-term-memory", {'query': 'rust release', 'person': ''})` | none selected | A later request uses what an earlier one learned |
| Objectives | `live-objectives` | `hubofhubs.run("live-objectives", '')` | none selected | An objective persists until it is met |
| Intuition | `the-intuition` | `hubofhubs.run("the-intuition", {'request': 'what is the latest Rust release?'})` | none selected | Unasked items are taken and useful |
| Context Intake | `context-intake` | `hubofhubs.run("context-intake", {'request': 'what is the latest Rust release?'})` | Merge into one labelled view (`one_view`) | One view with every source named |
| Request Planner | `request-planner` | `hubofhubs.run("request-planner", {'request': 'what is the latest Rust release?'})` | Split and route by cues (`cue_router`) | Requests routed to the right worker |
| Work Delegation | `work-delegation` | `hubofhubs.run("work-delegation", {'pieces': [], 'authority': {}})` | Route to Tools and Science (`to_tools`) | Handoffs keep authority, budget and cancellation |
| Response Writer | `response-writer` | `hubofhubs.run("response-writer", {'results': [], 'profile': None})` | Cited results (`cited_results`) | Responses that say what the results hold |
| Planner Guidance | `planner-guidance` | `hubofhubs.run("planner-guidance", ...)` | none selected | A nudge that helps the Planner |
| ESOI Application | `esoi-application` | `hubofhubs.run("esoi-application", {'change': {}})` | none selected | Specs and metrics improve by the loop |
| Metric Translation | `metric-translation` | `hubofhubs.run("metric-translation", {'request': 'what is the latest Rust release?'})` | Goal record with default budget (`goal_record`) | A goal record with a target and a budget |
| Goal Completion | `goal-completion` | `hubofhubs.run("goal-completion", ...)` | Evidence standard (`evidence_standard`) | Goals judged met only when they are |
| Response Quality | `response-quality` | `hubofhubs.run("response-quality", ...)` | Links held to their evidence (`evidence_check`) | Balanced score of a response against its quality profile |
| Cards From Files | `cards-from-files` | `hubofhubs.run("cards-from-files", {'root': '.', 'files': [], 'existing': {}})` | Import graph topic cards (`import_graph_topic_cards`) | Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size |
| Proactivity | `the-proactivity` | `hubofhubs.run("the-proactivity", {'schedules': [], 'now': '2026-07-12T09:00:00Z'})` | Calendar periods and events (`calendar_and_events`) | Schedules due when they should be |

## Problems and ideals

**Problems**

- Guards without proven value (`hprob-addon-guard-without-marginal-value`): A guard or reviewer added around a model or harness is kept because it sounds careful, without showing that it catches anything the model or harness would not catch alone.
- Context too broad or missing (`hprob-context-too-broad-or-missing`): A task is shown too much of a codebase, the wrong part of it, or context it never needed, so the model pays for noise or misses the file that matters.
- Two intakes wired by hand (`hprob-mind-has-two-intakes-wired-by-hand`): What the Mind sees for a request comes from two sources, the system's internal context and the outside, and each product wires both to the Mind its own way.
- Answers outrun their evidence (`hprob-answers-outrun-their-evidence`): An answer claims more than the evidence behind it supports, and the reader cannot tell which claim is unsupported.
- Long view lost between requests (`hprob-long-view-lost-between-requests`): Each request starts from nothing: what happened before, what stays true and what the AI is working toward are lost between requests.
- One prompt carries every instruction (`hprob-one-prompt-carries-every-instruction`): Every task's prompt carries every standing instruction and every correction ever given, so cost grows and quality falls as instructions accumulate.
- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request does not know the authority it carries or what done means for that piece.
- Goal not turned into a metric (`hprob-goal-not-turned-into-a-metric`): A request is answered without a target, so no one can say whether its goal was met or how much better a second try was.
- One quality standard for everyone (`hprob-one-quality-standard-for-everyone`): Response quality is judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.
- Files without cards (`hprob-files-without-cards`): A consumer whose knowledge lives in files has no cards for it until something writes them, and cards written once go stale as the files change.
- and 1 more: all 11 are in [problems](#problems) of the full record below

**Ideals**

- The context a task needs, and little else (`hideal-context-needed-and-little-else`): A task is shown the pieces it needs, in order of need, within a budget, and nothing when it needs nothing.
- One intake, two sources (`hideal-one-intake-two-sources`): The Mind has one intake fed by the system's internal context and by the outside.
- Answers stay within their evidence (`hideal-answers-stay-within-evidence`): Every claim in an answer is supported by evidence the reader can open, or is marked as unsupported.
- The long view is kept (`hideal-the-long-view-is-kept`): What happened, what stays true and what the AI is working toward survive from one request to the next.
- Only the instructions a task needs (`hideal-only-the-instructions-a-task-needs`): A task is given the instructions that bear on it and no others, and its prompt is an implementation measured on quality and cost.
- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.
- Every request has a target (`hideal-every-request-has-a-target`): Every request and sub-goal has a metric with a target value or an improvement, which rolls up to the objective it serves.
- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is judged against the quality profile of the person and situation, with a researched default when none is given.
- The system acts on time (`hideal-the-system-acts-on-time`): The system starts its standing work when it is due, by calendar period in the person's own zone, when a run is requested, or when something happened.

## Metrics and their leaders

- Risky steps stopped, ordinary steps let through (`metric-nervous-system`): leader `two_stage`, 34 of 36 cases
- Guard marginal value (`metric-guard-marginal-value-over-native-and-harness`)
- Requests with a named problem, ideal and metric (`metric-critical-thinking`)
- Answer quality per dollar and per second (`metric-the-mind`)
- Right context admitted, none from another scope (`metric-the-subconscious`)
- Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources (`metric-context-retriever`): leader `bm25_body`, 203 of 395 cases
- The long view survives between requests (`metric-higher-mind`)
- A later request uses what an earlier one learned (`metric-long-term-memory`)
- An objective persists until it is met (`metric-live-objectives`)
- Unasked items are taken and useful (`metric-the-intuition`)
- and 11 more: all 21 are in [metrics](#metrics) of the full record below

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- Guards without proven value (`hprob-addon-guard-without-marginal-value`): A guard or reviewer added around a model or harness is kept because it sounds careful, without showing that it catches anything the model or harness would not catch alone.
- Context too broad or missing (`hprob-context-too-broad-or-missing`): A task is shown too much of a codebase, the wrong part of it, or context it never needed, so the model pays for noise or misses the file that matters.
- Two intakes wired by hand (`hprob-mind-has-two-intakes-wired-by-hand`): What the Mind sees for a request comes from two sources, the system's internal context and the outside, and each product wires both to the Mind its own way.
- Answers outrun their evidence (`hprob-answers-outrun-their-evidence`): An answer claims more than the evidence behind it supports, and the reader cannot tell which claim is unsupported.
- Long view lost between requests (`hprob-long-view-lost-between-requests`): Each request starts from nothing: what happened before, what stays true and what the AI is working toward are lost between requests.
- One prompt carries every instruction (`hprob-one-prompt-carries-every-instruction`): Every task's prompt carries every standing instruction and every correction ever given, so cost grows and quality falls as instructions accumulate.
- Handoff loses authority and done standard (`hprob-handoff-loses-authority-and-done-standard`): A worker given one piece of a request does not know the authority it carries or what done means for that piece.
- Goal not turned into a metric (`hprob-goal-not-turned-into-a-metric`): A request is answered without a target, so no one can say whether its goal was met or how much better a second try was.
- One quality standard for everyone (`hprob-one-quality-standard-for-everyone`): Response quality is judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.
- Files without cards (`hprob-files-without-cards`): A consumer whose knowledge lives in files has no cards for it until something writes them, and cards written once go stale as the files change.
- The system only reacts (`hprob-system-waits-to-be-asked`): An AI that acts only when asked misses the standing work (a daily review, a weekly report) and the moment something changed, so people must remember to ask.

### Ideals

- The context a task needs, and little else (`hideal-context-needed-and-little-else`): A task is shown the pieces it needs, in order of need, within a budget, and nothing when it needs nothing.
- One intake, two sources (`hideal-one-intake-two-sources`): The Mind has one intake fed by the system's internal context and by the outside.
- Answers stay within their evidence (`hideal-answers-stay-within-evidence`): Every claim in an answer is supported by evidence the reader can open, or is marked as unsupported.
- The long view is kept (`hideal-the-long-view-is-kept`): What happened, what stays true and what the AI is working toward survive from one request to the next.
- Only the instructions a task needs (`hideal-only-the-instructions-a-task-needs`): A task is given the instructions that bear on it and no others, and its prompt is an implementation measured on quality and cost.
- Every handoff carries authority and a standard (`hideal-every-handoff-carries-authority-and-done-standard`): Each handoff names the authority it carries and the done-standard of its sub-goal.
- Every request has a target (`hideal-every-request-has-a-target`): Every request and sub-goal has a metric with a target value or an improvement, which rolls up to the objective it serves.
- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is judged against the quality profile of the person and situation, with a researched default when none is given.
- The system acts on time (`hideal-the-system-acts-on-time`): The system starts its standing work when it is due, by calendar period in the person's own zone, when a run is requested, or when something happened.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Nervous System | `nervous-system` | Consent gate (`consent_gate`) | Risky steps stopped, ordinary steps let through, Guard marginal value |
| Critical Thinking | `critical-thinking` | Target, goal and quality in order (`composition`) | Requests with a named problem, ideal and metric |
| Subconscious | `the-subconscious` | Cards drawn by relevance from a store (`card_recall`) | Right context admitted, none from another scope |
| Context Retriever | `context-retriever` | BM25 over chunk text (`bm25_body`) | Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources |
| Mind | `the-mind` | The four parts of the Mind in order (`composition`) | Answer quality per dollar and per second |
| Higher Mind | `higher-mind` | Objectives, memory and guidance for one request (`composition`) | The long view survives between requests |
| Long-Term Memory | `long-term-memory` | none selected | A later request uses what an earlier one learned |
| Objectives | `live-objectives` | none selected | An objective persists until it is met |
| Intuition | `the-intuition` | none selected | Unasked items are taken and useful |
| Context Intake | `context-intake` | Merge into one labelled view (`one_view`) | One view with every source named |
| Request Planner | `request-planner` | Split and route by cues (`cue_router`) | Requests routed to the right worker |
| Work Delegation | `work-delegation` | Route to Tools and Science (`to_tools`) | Handoffs keep authority, budget and cancellation |
| Response Writer | `response-writer` | Cited results (`cited_results`) | Responses that say what the results hold |
| Planner Guidance | `planner-guidance` | none selected | A nudge that helps the Planner |
| ESOI Application | `esoi-application` | none selected | Specs and metrics improve by the loop |
| Metric Translation | `metric-translation` | Goal record with default budget (`goal_record`) | A goal record with a target and a budget |
| Goal Completion | `goal-completion` | Evidence standard (`evidence_standard`) | Goals judged met only when they are |
| Response Quality | `response-quality` | Links held to their evidence (`evidence_check`) | Balanced score of a response against its quality profile |
| Cards From Files | `cards-from-files` | Import graph topic cards (`import_graph_topic_cards`) | Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size |
| Proactivity | `the-proactivity` | Calendar periods and events (`calendar_and_events`) | Schedules due when they should be |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Digest-driven overseer | `nervous-system:overseer` | [hubofhubs/risk.py](../risk.py) |  |
| Consent gate | `nervous-system:consent_gate` | [hubofhubs/consent_gate.py](../consent_gate.py) |  |
| Gate then overseer | `nervous-system:two_stage` | [hubofhubs/consent_gate.py](../consent_gate.py) |  |
| Links held to their evidence | `response-quality:evidence_check` | [hubofhubs/critique/evidence_check.py](../critique/evidence_check.py) |  |
| Cards drawn by relevance from a store | `the-subconscious:card_recall` | [hubofhubs/recall/card_recall.py](../recall/card_recall.py) |  |
| BM25 over chunk text | `context-retriever:bm25_body` | [hubofhubs/retrieval/lexical.py](../retrieval/lexical.py) |  |
| BM25F over path, title and body | `context-retriever:bm25_fielded` | [hubofhubs/retrieval/lexical.py](../retrieval/lexical.py) |  |
| BM25F over whole files | `context-retriever:bm25_whole_files` | [hubofhubs/retrieval/lexical.py](../retrieval/lexical.py) |  |
| Latent semantic index | `context-retriever:lsi` | [hubofhubs/retrieval/dense.py](../retrieval/dense.py) |  |
| Dense bge-small vectors | `context-retriever:dense_bge_small` | [hubofhubs/retrieval/dense.py](../retrieval/dense.py) |  |
| BM25F and dense by rank fusion | `context-retriever:hybrid_rrf` | [hubofhubs/retrieval/fusion.py](../retrieval/fusion.py) |  |
| Local feature reranker | `context-retriever:feature_rerank` | [hubofhubs/retrieval/fusion.py](../retrieval/fusion.py) |  |
| Feature reranker without priors | `context-retriever:feature_rerank_no_priors` | [hubofhubs/retrieval/fusion.py](../retrieval/fusion.py) |  |
| Learned reranker | `context-retriever:learned_rerank` | [hubofhubs/retrieval/learned.py](../retrieval/learned.py) |  |
| Hybrid that can say nothing | `context-retriever:abstaining_hybrid` | [hubofhubs/retrieval/abstain.py](../retrieval/abstain.py) |  |
| Learned reranker that can say nothing | `context-retriever:abstaining_learned` | [hubofhubs/retrieval/abstain.py](../retrieval/abstain.py) |  |
| Model reranker | `context-retriever:llm_rerank` | [hubofhubs/retrieval/abstain.py](../retrieval/abstain.py) |  |
| Hybrid that prefers newer items | `context-retriever:abstaining_recency` | [hubofhubs/retrieval/aware.py](../retrieval/aware.py) |  |
| Hybrid with soft affinity to the request's focus | `context-retriever:abstaining_affinity` | [hubofhubs/retrieval/aware.py](../retrieval/aware.py) |  |
| Hybrid with recency, affinity and supersession | `context-retriever:abstaining_aware` | [hubofhubs/retrieval/aware.py](../retrieval/aware.py) |  |
| Hybrid behind a hard focus fence | `context-retriever:abstaining_fenced` | [hubofhubs/retrieval/aware.py](../retrieval/aware.py) |  |
| Scan of the live sources | `context-retriever:live_scan` | [hubofhubs/retrieval/aware.py](../retrieval/aware.py) |  |
| Objectives, memory and guidance for one request | `higher-mind:composition` | [hubofhubs/flows.py](../flows.py) |  |
| The four parts of the Mind in order | `the-mind:composition` | [hubofhubs/flows.py](../flows.py) |  |
| Target, goal and quality in order | `critical-thinking:composition` | [hubofhubs/flows.py](../flows.py) |  |
| Model-written topic cards | `cards-from-files:llm_topic_cards` | [hubofhubs/recall/cards_from_files.py](../recall/cards_from_files.py) |  |
| One card per file | `cards-from-files:per_file_symbols` | [hubofhubs/recall/cards_from_files.py](../recall/cards_from_files.py) |  |
| Graphify file groups | `cards-from-files:graphify_files` | [hubofhubs/recall/cards_from_graphify.py](../recall/cards_from_graphify.py) |  |
| File plus topic cards | `cards-from-files:file_plus_topic_cards` | [hubofhubs/recall/cards_from_files.py](../recall/cards_from_files.py) |  |
| Topic cards replay | `cards-from-files:topic_cards_replay` | [hubofhubs/recall/cards_from_files.py](../recall/cards_from_files.py) |  |
| Cochange topic cards | `cards-from-files:cochange_topic_cards` | [hubofhubs/recall/cards_from_topics.py](../recall/cards_from_topics.py) |  |
| Import graph topic cards | `cards-from-files:import_graph_topic_cards` | [hubofhubs/recall/cards_from_topics.py](../recall/cards_from_topics.py) |  |
| Merge into one labelled view | `context-intake:one_view` | [hubofhubs/orchestrate/intake.py](../orchestrate/intake.py) |  |
| Evidence standard | `goal-completion:evidence_standard` | [hubofhubs/critique/goal_completion.py](../critique/goal_completion.py) |  |
| Outcome is not empty | `goal-completion:nonempty` | [hubofhubs/critique/goal_completion.py](../critique/goal_completion.py) |  |
| Goal record with default budget | `metric-translation:goal_record` | [hubofhubs/orchestrate/translation.py](../orchestrate/translation.py) |  |
| Calendar periods and events | `the-proactivity:calendar_and_events` | [hubofhubs/proactivity/triggers.py](../proactivity/triggers.py) |  |
| Elapsed hours | `the-proactivity:elapsed_hours` | [hubofhubs/proactivity/triggers.py](../proactivity/triggers.py) |  |
| Split and route by cues | `request-planner:cue_router` | [hubofhubs/orchestrate/planning.py](../orchestrate/planning.py) |  |
| One piece, no worker | `request-planner:one_piece` | [hubofhubs/orchestrate/planning.py](../orchestrate/planning.py) |  |
| Cited results | `response-writer:cited_results` | [hubofhubs/orchestrate/writer.py](../orchestrate/writer.py) |  |
| Model synthesis | `response-writer:model_synthesis` | [hubofhubs/orchestrate/writer.py](../orchestrate/writer.py) |  |
| Route to Tools and Science | `work-delegation:to_tools` | [hubofhubs/orchestrate/delegation.py](../orchestrate/delegation.py) |  |

### Metrics

- Risky steps stopped, ordinary steps let through (`metric-nervous-system`): `esoi run watch_for_risk --impl overseer; esoi run watch_for_risk --impl none; esoi run watch_for_risk --impl consent_gate; esoi run watch_for_risk --impl two_stage`
- Guard marginal value (`metric-guard-marginal-value-over-native-and-harness`): `python3 -m pytest tests/test_risk.py`
- Requests with a named problem, ideal and metric (`metric-critical-thinking`): `none`
- Answer quality per dollar and per second (`metric-the-mind`): `none`
- Right context admitted, none from another scope (`metric-the-subconscious`): `none`
- Balanced score of retrieval on file, topic, orientation, no-context, memory, public-repository and grouping requests, with the index size and the cost of reading sources (`metric-context-retriever`): `esoi run context_retrieval --impl bm25_body; esoi run context_retrieval --impl bm25_fielded; esoi run context_retrieval --impl bm25_whole_files; esoi run context_retrieval --impl lsi; esoi run context_retrieval --impl dense_bge_small; esoi run context_retrieval --impl hybrid_rrf; esoi run context_retrieval --impl feature_rerank; esoi run context_retrieval --impl feature_rerank_no_priors; esoi run context_retrieval --impl learned_rerank; esoi run context_retrieval --impl abstaining_hybrid; esoi run context_retrieval --impl abstaining_learned; esoi run context_retrieval --impl abstaining_recency; esoi run context_retrieval --impl abstaining_affinity; esoi run context_retrieval --impl abstaining_aware; esoi run context_retrieval --impl abstaining_fenced; esoi run context_retrieval --impl live_scan; esoi run context_retrieval --impl llm_rerank`
- The long view survives between requests (`metric-higher-mind`): `none`
- A later request uses what an earlier one learned (`metric-long-term-memory`): `none`
- An objective persists until it is met (`metric-live-objectives`): `none`
- Unasked items are taken and useful (`metric-the-intuition`): `none`
- One view with every source named (`metric-context-intake`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Requests routed to the right worker (`metric-request-planner`): `esoi run request_planning --impl cue_router; esoi run request_planning --impl one_piece`
- Handoffs keep authority, budget and cancellation (`metric-work-delegation`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Responses that say what the results hold (`metric-response-writer`): `esoi run response_writing --impl cited_results`
- A nudge that helps the Planner (`metric-planner-guidance`): `none`
- Specs and metrics improve by the loop (`metric-esoi-application`): `none`
- A goal record with a target and a budget (`metric-metric-translation`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Goals judged met only when they are (`metric-goal-completion`): `esoi run goal_completion --impl evidence_standard; esoi run goal_completion --impl nonempty`
- Balanced score of a response against its quality profile (`metric-response-quality`): `none`
- Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size (`metric-cards-from-files`): `esoi run cards_from_files --impl llm_topic_cards; esoi run cards_from_files --impl topic_cards_replay; esoi run cards_from_files --impl cochange_topic_cards; esoi run cards_from_files --impl import_graph_topic_cards; esoi run cards_from_files --impl file_plus_topic_cards; esoi run cards_from_files --impl per_file_symbols; esoi run cards_from_files --impl graphify_files`
- Schedules due when they should be (`metric-proactivity`): `esoi run proactivity --impl calendar_and_events; esoi run proactivity --impl elapsed_hours`
