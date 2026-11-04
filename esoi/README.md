# The best parts for AI intelligence, assembled and proven

Anyone building AI intelligence can assemble a working system from the best open-source parts available, chosen by measurement and kept current every week, without writing the glue themselves.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

Opportunities: Any product that needs an AI grounded in a person or team's own goals can start from the assembled whole instead of researching and gluing parts again; a production consumer is the hardest test of the assembly.

## How the solutions fit together

hub-of-hubs gives anyone a working AI assembled from measured open-source parts, and The whole being is the one call that holds the mind together. It answers a question through World in and Subconscious, Intuition, holds that answer to its sources through Critical thinking, asks a model at a measured tier through the Mind, shows a task the pieces of a folder's files it needs, within a token budget or not at all, through the context retriever, carries a goal out through the Body only after the Overseer lets the step pass, and checks that the hub stays generic through Character. World in brings outside material in by running a web search through web search and, for research questions, a paper lookup through Science. Subconscious, Intuition keeps cards in the card store, draws the cards a query needs by relevance through the context assembler, and fills the store from a folder's files through cards from files. Cards from files groups a folder's files into topic cards by which files import each other, so it writes them without asking a model. The Mind sends a question to the model that the model tier chooser measured best for the tier, through the model call, which is built on the vendor model caller. The Body makes each file edit with a single request through the vendor model caller, at the tier that the model tier chooser picks. Character audits the hub for consumer wording and learns how stale its research is through Learning. Character also learns how much of the hub connects by configuration through Hands. Learning lists the areas whose research is older than ninety days by reading their dates through the research freshness reader. Hands reports the share of connections that need no code by scoring them through the connection scorer.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["World in<br/><i>take-in-the-world</i>"]
    s1["Mind<br/><i>reason-and-answer</i>"]
    s2["Model tier chooser<br/><i>choose-a-model-tier</i>"]
    s3["Science<br/><i>know-the-world</i>"]
    s4["Body<br/><i>act-in-the-world</i>"]
    s5["Overseer<br/><i>watch-for-risk</i>"]
    s6["The whole being<br/><i>assemble-the-whole</i>"]
    s7["Learning<br/><i>stay-current</i>"]
    s8["Research freshness reader<br/><i>read-registry-freshness</i>"]
    s9["Character<br/><i>keep-it-generic</i>"]
    s10["Hands<br/><i>connect-any-integration</i>"]
    s11["Connection scorer<br/><i>score-hub-connections</i>"]
    s12["Card store<br/><i>card-store</i>"]
    s13["Critical thinking<br/><i>think-critically</i>"]
    s14["Model call<br/><i>model-call</i>"]
    s15["Vendor model caller<br/><i>call-a-model</i>"]
    s16["Subconscious, Intuition<br/><i>remember-and-recall</i>"]
    s17["Context assembler<br/><i>context-assembler</i>"]
    s18["Cards from files<br/><i>cards-from-files</i>"]
    s19["Context retriever<br/><i>retrieve-context</i>"]
    s20["Web search<br/><i>search-backend</i>"]
    s0 -->|"Outside material for a task, from the search backends"| s6
    s1 -->|"The text a model answers to the prompt at that tier"| s6
    s2 -->|"A mapping from each tier to the chosen provider and model"| s1
    s2 -->|"A mapping from each tier to the chosen provider and model"| s4
    s3 -->|"One observation: title, link and snippet per hit, or the..."| s0
    s4 -->|"A DeepResult that says whether the goal was met, with the..."| s6
    s5 -->|"One signal: proceed, redirect, answer_now, escalate_deep or..."| s6
    s7 -->|"The names of the registry's areas whose research is older..."| s9
    s8 -->|"Days since the date, or the combined freshness reading with..."| s7
    s9 -->|"Seats whose wording is data, whose arms are current and..."| s6
    s10 -->|"The share, from 0 to 1, of the area's hub connections that..."| s9
    s11 -->|"Per-area checks and a combined score"| s10
    s12 -->|"The id of an added card, a card or nothing for an id, the..."| s16
    s13 -->|"The findings, one per claim the evidence does not support..."| s6
    s14 -->|"The text a model answers to the prompt"| s1
    s14 -->|"The text a model answers to the prompt"| s3
    s15 -->|"Text, a plan or a list of models"| s4
    s15 -->|"Text, a plan or a list of models"| s5
    s15 -->|"Text, a plan or a list of models"| s14
    s15 -->|"Text, a plan or a list of models"| s18
    s15 -->|"Text, a plan or a list of models"| s19
    s16 -->|"The cards a task needs, in one rendered view with their ids"| s6
    s17 -->|"An assembled context view and the ids of the cards it drew..."| s16
    s18 -->|"Cards in the card-store record shape (grouping, summary..."| s16
    s19 -->|"Hits: unit id, file, first line, score, tokens and text..."| s6
    s19 -->|"Hits: unit id, file, first line, score, tokens and text..."| s17
    s20 -->|"A response of hits (title, link, snippet, date, passages..."| s0
    s20 -->|"A response of hits (title, link, snippet, date, passages..."| s3
```

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| World in | `take-in-the-world` | `hubofhubs.run("take-in-the-world", 'latest Rust release')` | `search_backends` | World in measure (draft) |
| Mind | `reason-and-answer` | `hubofhubs.run("reason-and-answer", ...)` | `model_calls` | Mind measure (draft) |
| Model tier chooser | `choose-a-model-tier` | `hubofhubs.run("choose-a-model-tier", {'available': ['anthropic']})` | `tier_selector` | Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer |
| Science | `know-the-world` | `hubofhubs.run("know-the-world", 'meditation and attention')` | `openalex_semantic` | Research question finds its paper |
| Body | `act-in-the-world` | `hubofhubs.run("act-in-the-world", ...)` | `fast_edit` | Goal met by its own tests, Harness, context, sub-agents and recursion ranked |
| Overseer | `watch-for-risk` | `hubofhubs.run("watch-for-risk", 'delete the old backup folder')` | `consent_gate` | Risky steps stopped, ordinary steps let through, Guard marginal value |
| The whole being | `assemble-the-whole` | `hubofhubs.run("assemble-the-whole", 'what is the latest Rust release?')` | `zero_config` | Whole assembly, Capability of the whole from the user's seat, Consent floor, Honesty floor |
| Learning | `stay-current` | `hubofhubs.run("stay-current", '2026-11-03')` | `registry_research` | Learning measure (draft), Public stage sourced and triangulated, Best in circumstance with variants |
| Research freshness reader | `read-registry-freshness` | `hubofhubs.run("read-registry-freshness", '2026-10-01')` | `registry_scan` | Registry freshness reading |
| Character | `keep-it-generic` | `hubofhubs.run("keep-it-generic", ['examplevendor'])` | `prompts_as_data` | Character measure (draft), Intents whose solutions one paragraph and one diagram explain as the code builds them |
| Hands | `connect-any-integration` | `hubofhubs.run("connect-any-integration", 'web_search')` | `catalog_entries` | Integration added with zero code (draft), Integration served by combined hubs |
| Connection scorer | `score-hub-connections` | `hubofhubs.run("score-hub-connections", {'facts': {}, 'connections': []})` | `hub_of_hubs_scorer` | Hub connection scoring |
| Card store | `card-store` | `hubofhubs.run("card-store", 'rust release')` | `local_card_store` | Cards found again, none lost |
| Critical thinking | `think-critically` | `hubofhubs.run("think-critically", ...)` | `evidence_check` | Critical thinking measure (draft) |
| Model call | `model-call` | `hubofhubs.run("model-call", ...)` | `via_call_a_model` | Model call answers for the tier |
| Vendor model caller | `call-a-model` | `hubofhubs.run("call-a-model", ...)` | `claude_cli` | Provider failover |
| Subconscious, Intuition | `remember-and-recall` | `hubofhubs.run("remember-and-recall", 'rust release')` | `card_recall` | Subconscious, Intuition measure (draft) |
| Context assembler | `context-assembler` | `hubofhubs.run("context-assembler", 'where does the card store tidy itself?')` | `bm25@analyzer=english` | Relevant passage in the top five |
| Cards from files | `cards-from-files` | `hubofhubs.run("cards-from-files", {'root': '.', 'files': [], 'existing': {}})` | `import_graph_topic_cards` | Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size |
| Context retriever | `retrieve-context` | `hubofhubs.run("retrieve-context", ...)` | `abstaining_hybrid` | Balanced score of retrieval on file, topic, orientation and no-context requests, with the index size |
| Web search | `search-backend` | `hubofhubs.run("search-backend", 'latest Rust release')` | `gemini` | Search finds the source |

## Problems and ideals

**Problems**

- `HP1`: Every team re-researches and re-glues the same AI parts, and the private copies drift apart.
- `HP2`: Lists of hubs say what exists, not which works best or fits together.
- `HP3`: Hubs go stale.
- `HP4`: One hub's outage, price change or shutdown stops the system, and switching needs code changes.
- `HP5`: Parts that are best alone can fail when assembled, and nobody tests the whole.
- `HP6`: One product's prompts and settings leak into shared code, so it cannot be reused by anyone else.
- `HP7`: Every product re-builds each app connection (calendar, drive, notes, chat) with its own screen, storage and tool code, so a new app costs code in every layer and arrives months after hubs list it.
- `hprob-assembly-not-jarvis-from-the-users-seat`: An assembled system is judged part by part, so nobody checks that it behaves like one capable assistant from where the user sits: asked for something real, it should know what it may do, ask before...
- `hprob-public-evals-relied-on-singly`: One public benchmark is trusted alone to rank parts, although it may measure a different task, be saturated or leaked into training data, and its source is rarely checked.
- `hprob-one-best-pick-ignores-circumstance`: A part is ranked best overall, but which part is best depends on the circumstance (a cost limit, a speed limit, a language, the size of the input), so the single winner is wrong for many users.
- and 5 more: all 15 are in [problems](#problems) of the full record below

**Ideals**

- Best by measurement (`HI1`): Each seat holds the part that measures best on shared cases.
- One-step assembly (`HI2`): Configuration in, working system out, no glue code.
- Always current (`HI3`): No area goes a week without a fresh search and comparison.
- Swappable parts (`HI4`): Any part can be replaced by configuration when another measures better or fails.
- Proven whole (`HI5`): The assembled system is tested end to end on a production consumer, not only part by part.
- Generic and thin (`HI6`): No consumer-specific content.
- Capable from the user's seat (`hideal-jarvis-from-the-users-seat`): The assembled hub is judged as the user meets it: one capable assistant that gets real work done, asks before it does anything that cannot be undone, and reports only what it did.
- Common-sense metrics, sourced stages (`hideal-common-sense-metrics-with-sourced-stages`): Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- Best in each circumstance, with variants (`hideal-best-in-circumstance-with-variants`): The hub names the best part for each circumstance and not one winner, by comparing variants of a part (one setting changed) on the same cases.
- Guards earn their place (`hideal-guards-earn-their-place`): A guard is kept only when it catches something the model or harness would miss, shown by running the same cases with and without it.
- and 4 more: all 14 are in [ideals](#ideals) of the full record below

## Metrics and their leaders

- World in measure (draft) (`metric-take-in-the-world`)
- Mind measure (draft) (`metric-reason-and-answer`)
- Tier choice by passing work per cost (`metric-choose-a-model-tier`): leader `tier_selector`, 36 of 36 cases
- Research question finds its paper (`metric-know-the-world`): leader `openalex_semantic`, 52 of 150 cases
- Goal met by its own tests (`metric-act-in-the-world`): leader `fast_edit`, 29 of 30 cases
- Risky steps stopped, ordinary steps let through (`metric-watch-for-risk`): leader `two_stage`, 34 of 36 cases
- Whole assembly (`metric-assemble-the-whole`)
- Learning measure (draft) (`metric-stay-current`)
- Registry freshness reading (`metric-read-registry-freshness`): leader `registry_scan`, 41 of 41 cases
- Character measure (draft) (`metric-keep-it-generic`)
- and 25 more: all 35 are in [metrics](#metrics) of the full record below

## Where to go next

- Repository: [top README](../README.md)
- Records beside the code: [hubofhubs](../hubofhubs/README.md), [hubofhubs/act](../hubofhubs/act/README.md), [hubofhubs/critique](../hubofhubs/critique/README.md), [hubofhubs/deep](../hubofhubs/deep/README.md), [hubofhubs/models](../hubofhubs/models/README.md), [hubofhubs/recall](../hubofhubs/recall/README.md), [hubofhubs/retrieval](../hubofhubs/retrieval/README.md), [hubofhubs/science](../hubofhubs/science/README.md), [hubofhubs/websearch](../hubofhubs/websearch/README.md)
- Records: [intent.csv](intent.csv), [implementations.csv](implementations.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- `HP1`: Every team re-researches and re-glues the same AI parts, and the private copies drift apart.
- `HP2`: Lists of hubs say what exists, not which works best or fits together. Nothing evaluates the parts.
- `HP3`: Hubs go stale. A pick that was best last quarter quietly stops being best.
- `HP4`: One hub's outage, price change or shutdown stops the system, and switching needs code changes.
- `HP5`: Parts that are best alone can fail when assembled, and nobody tests the whole.
- `HP6`: One product's prompts and settings leak into shared code, so it cannot be reused by anyone else.
- `HP7`: Every product re-builds each app connection (calendar, drive, notes, chat) with its own screen, storage and tool code, so a new app costs code in every layer and arrives months after hubs list it.
- `hprob-assembly-not-jarvis-from-the-users-seat`: An assembled system is judged part by part, so nobody checks that it behaves like one capable assistant from where the user sits: asked for something real, it should know what it may do, ask before anything irreversible and say truthfully what it did.
- `hprob-public-evals-relied-on-singly`: One public benchmark is trusted alone to rank parts, although it may measure a different task, be saturated or leaked into training data, and its source is rarely checked.
- `hprob-one-best-pick-ignores-circumstance`: A part is ranked best overall, but which part is best depends on the circumstance (a cost limit, a speed limit, a language, the size of the input), so the single winner is wrong for many users.
- `hprob-addon-guard-without-marginal-value`: A guard or reviewer added around a model or harness is kept because it sounds careful, without showing that it catches anything the model or harness would not catch alone.
- `hprob-harness-dear-and-slow-on-the-subscription`: An agent harness used on a flat subscription is slow and spends more tokens than the work needs, partly because the context it is given is poor and partly because it repeats work through sub-agents and recursion.
- `hprob-one-integration-needs-several-hubs`: One app connection (a calendar, a drive, a chat) is served better by several hubs combined than by any one, but a product wires a single hub and hand-writes the rest.
- `hprob-files-without-cards`: A consumer whose knowledge lives in files has no cards for it until something writes them, and cards written once go stale as the files change.
- `hprob-context-too-broad-or-missing`: A task is shown too much of a codebase, the wrong part of it, or context it never needed, so the model pays for noise or misses the file that matters.

### Ideals

- Best by measurement (`HI1`): Each seat holds the part that measures best on shared cases. Taste never picks.
- One-step assembly (`HI2`): Configuration in, working system out, no glue code.
- Always current (`HI3`): No area goes a week without a fresh search and comparison.
- Swappable parts (`HI4`): Any part can be replaced by configuration when another measures better or fails.
- Proven whole (`HI5`): The assembled system is tested end to end on a production consumer, not only part by part.
- Generic and thin (`HI6`): No consumer-specific content. Defaults are data anyone can edit. Implementations stay in their own projects.
- Capable from the user's seat (`hideal-jarvis-from-the-users-seat`): The assembled hub is judged as the user meets it: one capable assistant that gets real work done, asks before it does anything that cannot be undone, and reports only what it did.
- Common-sense metrics, sourced stages (`hideal-common-sense-metrics-with-sourced-stages`): Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- Best in each circumstance, with variants (`hideal-best-in-circumstance-with-variants`): The hub names the best part for each circumstance and not one winner, by comparing variants of a part (one setting changed) on the same cases.
- Guards earn their place (`hideal-guards-earn-their-place`): A guard is kept only when it catches something the model or harness would miss, shown by running the same cases with and without it.
- Cheap, fast harness with ideal context (`hideal-cheap-fast-harness-with-ideal-context`): An agent harness is chosen for the lowest cost and time at the same pass rate, given the best context the hub can assemble for it, and the choice accounts for sub-agents and recursion.
- Hubs combined per integration (`hideal-hubs-combined-per-integration`): An integration is served by the combination of hubs that covers the most of it, chosen by data and never by one hub's reach.
- Proportionate, current cards (`hideal-cards-proportionate-and-current`): A folder's cards cover what is in it, about one card per thing people ask about, and change when the files change.
- The context a task needs, and little else (`hideal-context-needed-and-little-else`): A task is shown the pieces it needs, in order of need, within a budget, and nothing when it needs nothing.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| World in | `take-in-the-world` | search_backends | World in measure (draft) |
| Mind | `reason-and-answer` | model_calls | Mind measure (draft) |
| Model tier chooser | `choose-a-model-tier` | tier_selector | Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer |
| Science | `know-the-world` | openalex_semantic | Research question finds its paper |
| Body | `act-in-the-world` | fast_edit | Goal met by its own tests, Harness, context, sub-agents and recursion ranked |
| Overseer | `watch-for-risk` | consent_gate | Risky steps stopped, ordinary steps let through, Guard marginal value |
| The whole being | `assemble-the-whole` | zero_config | Whole assembly, Capability of the whole from the user's seat, Consent floor, Honesty floor |
| Learning | `stay-current` | registry_research | Learning measure (draft), Public stage sourced and triangulated, Best in circumstance with variants |
| Research freshness reader | `read-registry-freshness` | registry_scan | Registry freshness reading |
| Character | `keep-it-generic` | prompts_as_data | Character measure (draft), Intents whose solutions one paragraph and one diagram explain as the code builds them |
| Hands | `connect-any-integration` | catalog_entries | Integration added with zero code (draft), Integration served by combined hubs |
| Connection scorer | `score-hub-connections` | hub_of_hubs_scorer | Hub connection scoring |
| Card store | `card-store` | local_card_store | Cards found again, none lost |
| Critical thinking | `think-critically` | evidence_check | Critical thinking measure (draft) |
| Model call | `model-call` | via_call_a_model | Model call answers for the tier |
| Vendor model caller | `call-a-model` | claude_cli | Provider failover |
| Subconscious, Intuition | `remember-and-recall` | card_recall | Subconscious, Intuition measure (draft) |
| Context assembler | `context-assembler` | bm25@analyzer=english | Relevant passage in the top five |
| Cards from files | `cards-from-files` | import_graph_topic_cards | Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size |
| Context retriever | `retrieve-context` | abstaining_hybrid | Balanced score of retrieval on file, topic, orientation and no-context requests, with the index size |
| Web search | `search-backend` | gemini | Search finds the source |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Hand-wired general agent framework | `assemble-the-whole:hand_wired_agent_framework` |  |  |
| Registry date scan | `read-registry-freshness:registry_scan` | [hubofhubs/registry.py](../hubofhubs/registry.py) |  |
| Binding scorer | `score-hub-connections:hub_of_hubs_scorer` | [hubofhubs/measure.py](../hubofhubs/measure.py) |  |
| Passing work per cost selector | `choose-a-model-tier:tier_selector` | [hubofhubs/tiers.py](../hubofhubs/tiers.py) |  |
| Local card store | `card-store:local_card_store` | [hubofhubs/cardstore.py](../hubofhubs/cardstore.py) |  |
| Digest-driven overseer | `watch-for-risk:overseer` | [hubofhubs/risk.py](../hubofhubs/risk.py) |  |
| Consent gate | `watch-for-risk:consent_gate` | [hubofhubs/consent_gate.py](../hubofhubs/consent_gate.py) |  |
| Gate then overseer | `watch-for-risk:two_stage` | [hubofhubs/consent_gate.py](../hubofhubs/consent_gate.py) |  |
| One-call assembly of the whole hub | `assemble-the-whole:zero_config` | [hubofhubs/whole.py](../hubofhubs/whole.py) |  |
| Search and papers as the way in | `take-in-the-world:search_backends` | [hubofhubs/areas.py](../hubofhubs/areas.py) |  |
| Answers through the measured model for the tier | `reason-and-answer:model_calls` | [hubofhubs/areas.py](../hubofhubs/areas.py) |  |
| Audit of vendor wording, staleness and configuration | `keep-it-generic:prompts_as_data` | [hubofhubs/areas.py](../hubofhubs/areas.py) |  |
| Stale areas from the registry dates | `stay-current:registry_research` | [hubofhubs/areas.py](../hubofhubs/areas.py) |  |
| Share of connections that need no code | `connect-any-integration:catalog_entries` | [hubofhubs/areas.py](../hubofhubs/areas.py) |  |
| One-call file edit | `act-in-the-world:fast_edit` | [hubofhubs/act/fast_edit.py](../hubofhubs/act/fast_edit.py) |  |
| One-call MCP write | `act-in-the-world:mcp_operations` | [hubofhubs/act/mcp_operations.py](../hubofhubs/act/mcp_operations.py) |  |
| Links held to their evidence | `think-critically:evidence_check` | [hubofhubs/critique/evidence_check.py](../hubofhubs/critique/evidence_check.py) |  |
| Claude Code, one shot | `act-in-the-world:subprocess_goal_runner` | [hubofhubs/deep/subprocess_runner.py](../hubofhubs/deep/subprocess_runner.py) |  |
| Claude Code, steerable session | `act-in-the-world:stream_json_goal_runner` | [hubofhubs/deep/stream_runner.py](../hubofhubs/deep/stream_runner.py) |  |
| Agent Client Protocol runner | `act-in-the-world:acp_deep_runner` | [hubofhubs/deep/acp_runner.py](../hubofhubs/deep/acp_runner.py) |  |
| Anthropic provider | `call-a-model:anthropic` | [hubofhubs/models/anthropic.py](../hubofhubs/models/anthropic.py) |  |
| DeepSeek provider | `call-a-model:deepseek` | [hubofhubs/models/openai.py](../hubofhubs/models/openai.py) |  |
| Gemini provider | `call-a-model:gemini` | [hubofhubs/models/gemini.py](../hubofhubs/models/gemini.py) |  |
| Multi-provider router | `call-a-model:multi_provider` | [hubofhubs/models/router.py](../hubofhubs/models/router.py) |  |
| OpenAI provider | `call-a-model:openai` | [hubofhubs/models/openai.py](../hubofhubs/models/openai.py) |  |
| Built on the vendor model caller | `model-call:via_call_a_model` | [hubofhubs/models/via_provider.py](../hubofhubs/models/via_provider.py) |  |
| Claude Code CLI | `call-a-model:claude_cli` | [hubofhubs/models/claude_cli.py](../hubofhubs/models/claude_cli.py) |  |
| Composite | `context-assembler:composite` | [hubofhubs/recall/composite_assembler.py](../hubofhubs/recall/composite_assembler.py) |  |
| BM25 over file text | `context-assembler:bm25` | [hubofhubs/recall/bm25_store.py](../hubofhubs/recall/bm25_store.py) |  |
| Hybrid fusion | `context-assembler:hybrid` | [hubofhubs/recall/hybrid_assembler.py](../hubofhubs/recall/hybrid_assembler.py) |  |
| Vector search | `context-assembler:vector` | [hubofhubs/recall/vector_assembler.py](../hubofhubs/recall/vector_assembler.py) |  |
| Model-written topic cards | `cards-from-files:llm_topic_cards` | [hubofhubs/recall/cards_from_files.py](../hubofhubs/recall/cards_from_files.py) |  |
| One card per file | `cards-from-files:per_file_symbols` | [hubofhubs/recall/cards_from_files.py](../hubofhubs/recall/cards_from_files.py) |  |
| Graphify file groups | `cards-from-files:graphify_files` | [hubofhubs/recall/cards_from_graphify.py](../hubofhubs/recall/cards_from_graphify.py) |  |
| Cards drawn by relevance from a store | `remember-and-recall:card_recall` | [hubofhubs/recall/card_recall.py](../hubofhubs/recall/card_recall.py) |  |
| File plus topic cards | `cards-from-files:file_plus_topic_cards` | [hubofhubs/recall/cards_from_files.py](../hubofhubs/recall/cards_from_files.py) |  |
| Topic cards replay | `cards-from-files:topic_cards_replay` | [hubofhubs/recall/cards_from_files.py](../hubofhubs/recall/cards_from_files.py) |  |
| Cochange topic cards | `cards-from-files:cochange_topic_cards` | [hubofhubs/recall/cards_from_topics.py](../hubofhubs/recall/cards_from_topics.py) |  |
| Import graph topic cards | `cards-from-files:import_graph_topic_cards` | [hubofhubs/recall/cards_from_topics.py](../hubofhubs/recall/cards_from_topics.py) |  |
| Files through the context retriever | `context-assembler:file_retrieval` | [hubofhubs/recall/file_retrieval_assembler.py](../hubofhubs/recall/file_retrieval_assembler.py) |  |
| BM25 over chunk text | `retrieve-context:bm25_body` | [hubofhubs/retrieval/lexical.py](../hubofhubs/retrieval/lexical.py) |  |
| BM25F over path, title and body | `retrieve-context:bm25_fielded` | [hubofhubs/retrieval/lexical.py](../hubofhubs/retrieval/lexical.py) |  |
| BM25F over whole files | `retrieve-context:bm25_whole_files` | [hubofhubs/retrieval/lexical.py](../hubofhubs/retrieval/lexical.py) |  |
| Latent semantic index | `retrieve-context:lsi` | [hubofhubs/retrieval/dense.py](../hubofhubs/retrieval/dense.py) |  |
| Dense bge-small vectors | `retrieve-context:dense_bge_small` | [hubofhubs/retrieval/dense.py](../hubofhubs/retrieval/dense.py) |  |
| BM25F and dense by rank fusion | `retrieve-context:hybrid_rrf` | [hubofhubs/retrieval/fusion.py](../hubofhubs/retrieval/fusion.py) |  |
| Local feature reranker | `retrieve-context:feature_rerank` | [hubofhubs/retrieval/fusion.py](../hubofhubs/retrieval/fusion.py) |  |
| Feature reranker without priors | `retrieve-context:feature_rerank_no_priors` | [hubofhubs/retrieval/fusion.py](../hubofhubs/retrieval/fusion.py) |  |
| Learned reranker | `retrieve-context:learned_rerank` | [hubofhubs/retrieval/learned.py](../hubofhubs/retrieval/learned.py) |  |
| Hybrid that can say nothing | `retrieve-context:abstaining_hybrid` | [hubofhubs/retrieval/abstain.py](../hubofhubs/retrieval/abstain.py) |  |
| Learned reranker that can say nothing | `retrieve-context:abstaining_learned` | [hubofhubs/retrieval/abstain.py](../hubofhubs/retrieval/abstain.py) |  |
| Model reranker | `retrieve-context:llm_rerank` | [hubofhubs/retrieval/abstain.py](../hubofhubs/retrieval/abstain.py) |  |
| OpenAlex keyword search | `know-the-world:openalex` | [hubofhubs/science/openalex.py](../hubofhubs/science/openalex.py) |  |
| OpenAlex semantic search | `know-the-world:openalex_semantic` | [hubofhubs/science/openalex_semantic.py](../hubofhubs/science/openalex_semantic.py) |  |
| OpenAlex keywords, rule rewrite | `know-the-world:openalex_keywords` | [hubofhubs/science/openalex_keywords.py](../hubofhubs/science/openalex_keywords.py) |  |
| OpenAlex keywords, model rewrite | `know-the-world:openalex_keywords_model` | [hubofhubs/science/openalex_keywords.py](../hubofhubs/science/openalex_keywords.py) |  |
| Semantic and web paper search | `know-the-world:openalex_semantic_and_web` | [hubofhubs/science/openalex_semantic_and_web.py](../hubofhubs/science/openalex_semantic_and_web.py) |  |
| Brave Search API | `search-backend:brave` | [hubofhubs/websearch/backends.py](../hubofhubs/websearch/backends.py) |  |
| Gemini grounding | `search-backend:gemini` | [hubofhubs/websearch/gemini.py](../hubofhubs/websearch/gemini.py) |  |
| Provider-native search | `search-backend:provider` | [hubofhubs/websearch/backends.py](../hubofhubs/websearch/backends.py) |  |
| SearXNG | `search-backend:searxng` | [hubofhubs/websearch/backends.py](../hubofhubs/websearch/backends.py) |  |
| Serper | `search-backend:serper` | [hubofhubs/websearch/backends.py](../hubofhubs/websearch/backends.py) |  |
| Tavily | `search-backend:tavily` | [hubofhubs/websearch/backends.py](../hubofhubs/websearch/backends.py) |  |
| Web research | `know-the-world:web_research` | [hubofhubs/websearch/research.py](../hubofhubs/websearch/research.py) |  |

### Metrics

- World in measure (draft) (`metric-take-in-the-world`): `none`
- Mind measure (draft) (`metric-reason-and-answer`): `none`
- Tier choice by passing work per cost (`metric-choose-a-model-tier`): `esoi run reason_and_answer --impl tier_selector`
- Research question finds its paper (`metric-know-the-world`): `esoi run know_the_world --impl openalex_semantic_and_web; esoi run know_the_world --impl openalex_semantic; esoi run know_the_world --impl web_research; esoi run know_the_world --impl openalex; esoi run know_the_world --impl openalex_keywords; esoi run know_the_world --impl openalex_keywords_model`
- Goal met by its own tests (`metric-act-in-the-world`): `esoi run file_edit_goals --impl fast_edit; esoi run file_edit_goals --impl subprocess_goal_runner; esoi run file_edit_goals --impl stream_json_goal_runner; esoi run file_edit_goals --impl acp_deep_runner; esoi run file_edit_goals --impl none`
- Risky steps stopped, ordinary steps let through (`metric-watch-for-risk`): `esoi run watch_for_risk --impl overseer; esoi run watch_for_risk --impl none; esoi run watch_for_risk --impl consent_gate; esoi run watch_for_risk --impl two_stage`
- Whole assembly (`metric-assemble-the-whole`): `none`
- Learning measure (draft) (`metric-stay-current`): `none`
- Registry freshness reading (`metric-read-registry-freshness`): `esoi run stay_current --impl registry_scan`
- Character measure (draft) (`metric-keep-it-generic`): `none`
- Integration added with zero code (draft) (`metric-integration-added-with-zero-code`): `none`
- Hub connection scoring (`metric-score-hub-connections`): `esoi run connect_any_integration --impl hub_of_hubs_scorer`
- integration-availability-lag (draft) (`metric-integration-availability-lag`): `none`
- integration-credential-isolation (draft) (`metric-integration-credential-isolation`): `none`
- Tier passing work per cost (`metric-tier-passing-work-per-cost`): `python3 -m pytest tests/test_tiers.py`
- Cards found again, none lost (`metric-card-store`): `esoi run card_store --impl local_card_store`
- Capability of the whole from the user's seat (`metric-hub-jarvis-ness`): `none`
- Consent floor (`metric-hub-jarvis-floor-consent`): `none`
- Honesty floor (`metric-hub-jarvis-floor-honesty`): `none`
- Public stage sourced and triangulated (`metric-public-stage-sourced-and-triangulated`): `none`
- Best in circumstance with variants (`metric-best-in-circumstance-with-variants`): `none`
- Guard marginal value (`metric-guard-marginal-value-over-native-and-harness`): `python3 -m pytest tests/test_risk.py`
- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`): `python3 -m pytest tests/test_deep_session_subagents.py`
- Integration served by combined hubs (`metric-integration-served-by-combined-hubs`): `none`
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`): `python3 -m esoi.coherence --gate`
- Model quality on hard maths (`metric-model-quality`): `esoi run model_quality_aime --impl claude_haiku; esoi run model_quality_aime --impl claude_sonnet; esoi run model_quality_aime --impl claude_opus; esoi run model_quality_aime --impl gemini_2_5_flash_lite; esoi run model_quality_aime --impl gemini_2_5_flash; esoi run model_quality_aime --impl gpt_5_nano; esoi run model_quality_aime --impl gpt_5_mini; esoi run model_quality_aime --impl deepseek_flash`
- Vendor arms answer (`metric-vendor-answers`): `esoi run call_a_model --impl gemini; esoi run call_a_model --impl openai; esoi run call_a_model --impl deepseek; esoi run call_a_model --impl claude_cli`
- Critical thinking measure (draft) (`metric-think-critically`): `none`
- Model call answers for the tier (`metric-model-call`): `esoi run model_call --impl via_call_a_model`
- Provider failover (`metric-call-a-model`): `esoi run provider_failover --impl multi_provider`
- Subconscious, Intuition measure (draft) (`metric-remember-and-recall`): `none`
- Relevant passage in the top five (`metric-context-assembler`): `esoi run context_assembler --impl bm25; esoi run context_assembler --impl vector; esoi run context_assembler --impl hybrid; esoi run context_assembler --impl composite`
- Balanced score of a builder's cards on file-finding, topic and orientation cases, with the store's size (`metric-cards-from-files`): `esoi run cards_from_files --impl llm_topic_cards; esoi run cards_from_files --impl topic_cards_replay; esoi run cards_from_files --impl cochange_topic_cards; esoi run cards_from_files --impl import_graph_topic_cards; esoi run cards_from_files --impl file_plus_topic_cards; esoi run cards_from_files --impl per_file_symbols; esoi run cards_from_files --impl graphify_files`
- Balanced score of retrieval on file, topic, orientation and no-context requests, with the index size (`metric-retrieve-context`): `esoi run context_retrieval --impl bm25_body; esoi run context_retrieval --impl bm25_fielded; esoi run context_retrieval --impl bm25_whole_files; esoi run context_retrieval --impl lsi; esoi run context_retrieval --impl dense_bge_small; esoi run context_retrieval --impl hybrid_rrf; esoi run context_retrieval --impl feature_rerank; esoi run context_retrieval --impl feature_rerank_no_priors; esoi run context_retrieval --impl learned_rerank; esoi run context_retrieval --impl abstaining_hybrid; esoi run context_retrieval --impl abstaining_learned; esoi run context_retrieval --impl llm_rerank`
- Search finds the source (`metric-search-backend`): `esoi run search_backend --impl gemini; esoi run search_backend --impl provider; esoi run search_backend --impl searxng; esoi run search_backend --impl brave; esoi run search_backend --impl serper; esoi run search_backend --impl tavily`
