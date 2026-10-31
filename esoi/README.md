These are ESOI records (evolvable structure that optimizes intent): why this project exists, and its problems, solutions, implementations, ideals and metrics. This page is generated from the CSV files beside it by `esoi check --write-docs`; edit the CSV files, not this page.

# The best parts for AI intelligence, assembled and proven

unconfirmed: for Joshua to confirm. Anyone building AI intelligence can assemble a working system from the best open-source parts available, chosen by measurement and kept current every week, without writing the glue themselves.

## Problems

- `HP1`: unconfirmed: for Joshua to confirm. Every team re-researches and re-glues the same AI parts, and the private copies drift apart.
- `HP2`: unconfirmed: for Joshua to confirm. Lists of hubs say what exists, not which works best or fits together. Nothing evaluates the parts.
- `HP3`: unconfirmed: for Joshua to confirm. Hubs go stale. A pick that was best last quarter quietly stops being best.
- `HP4`: unconfirmed: for Joshua to confirm. One hub's outage, price change or shutdown stops the system, and switching needs code changes.
- `HP5`: unconfirmed: for Joshua to confirm. Parts that are best alone can fail when assembled, and nobody tests the whole.
- `HP6`: unconfirmed: for Joshua to confirm. One product's prompts and settings leak into shared code, so it cannot be reused by anyone else.
- `HP7`: unconfirmed: for Joshua to confirm. Every product re-builds each app connection (calendar, drive, notes, chat) with its own screen, storage and tool code, so a new app costs code in every layer and arrives months after hubs list it.
- `hprob-assembly-not-jarvis-from-the-users-seat`: unconfirmed: for Joshua to confirm. hprob-assembly-not-jarvis-from-the-users-seat
- `hprob-public-evals-relied-on-singly`: unconfirmed: for Joshua to confirm. hprob-public-evals-relied-on-singly
- `hprob-one-best-pick-ignores-circumstance`: unconfirmed: for Joshua to confirm. hprob-one-best-pick-ignores-circumstance
- `hprob-addon-guard-without-marginal-value`: unconfirmed: for Joshua to confirm. hprob-addon-guard-without-marginal-value
- `hprob-harness-dear-and-slow-on-the-subscription`: unconfirmed: for Joshua to confirm. hprob-harness-dear-and-slow-on-the-subscription
- `hprob-one-integration-needs-several-hubs`: unconfirmed: for Joshua to confirm. hprob-one-integration-needs-several-hubs

## Ideals

- `HI1`, Best by measurement: unconfirmed: for Joshua to confirm. Each seat holds the part that measures best on shared cases. Taste never picks.
- `HI2`, One-step assembly: unconfirmed: for Joshua to confirm. Configuration in, working system out, no glue code.
- `HI3`, Always current: unconfirmed: for Joshua to confirm. No area goes a week without a fresh search and comparison.
- `HI4`, Swappable parts: unconfirmed: for Joshua to confirm. Any part can be replaced by configuration when another measures better or fails.
- `HI5`, Proven whole: unconfirmed: for Joshua to confirm. The assembled system is tested end to end on a production consumer, not only part by part.
- `HI6`, Generic and thin: unconfirmed: for Joshua to confirm. No consumer-specific content. Defaults are data anyone can edit. Implementations stay in their own projects.
- `hideal-jarvis-from-the-users-seat`, unconfirmed: for Joshua to confirm.: unconfirmed: for Joshua to confirm.
- `hideal-common-sense-metrics-with-sourced-stages`, unconfirmed: for Joshua to confirm.: unconfirmed: for Joshua to confirm.
- `hideal-best-in-circumstance-with-variants`, unconfirmed: for Joshua to confirm.: unconfirmed: for Joshua to confirm.
- `hideal-guards-earn-their-place`, unconfirmed: for Joshua to confirm.: unconfirmed: for Joshua to confirm.
- `hideal-cheap-fast-harness-with-ideal-context`, unconfirmed: for Joshua to confirm.: unconfirmed: for Joshua to confirm.
- `hideal-hubs-combined-per-integration`, unconfirmed: for Joshua to confirm.: unconfirmed: for Joshua to confirm.

## Solutions

| Solution | Name | Selected | Metric |
|---|---|---|---|
| `hold-the-intents` | hold-the-intents: the Higher mind seat |  | hold-the-intents metric (draft) |
| `take-in-the-world` | take-in-the-world: the World seat |  | take-in-the-world metric (draft) |
| `remember-and-recall` | remember-and-recall: the Subconscious, Intuition seat |  | remember-and-recall metric (draft) |
| `reason-and-answer` | reason-and-answer: the Mind seat |  | reason-and-answer metric (draft) |
| `choose-a-model-tier` | choose-a-model-tier: pick the model for each tier | tier_selector | Tier choice by passing work per cost;Tier passing work per cost |
| `know-the-world` | know-the-world: the Science seat | web_research | Research question finds its paper |
| `think-critically` | think-critically: the Critical thinking seat |  | think-critically metric (draft) |
| `act-in-the-world` | act-in-the-world: the Body seat |  | Goal met by its own tests;unconfirmed: for Joshua to confirm. |
| `watch-for-risk` | watch-for-risk: the Overseer seat | overseer | Risky steps stopped, ordinary steps let through;unconfirmed: for Joshua to confirm. |
| `assemble-the-whole` | assemble-the-whole: the The whole being seat |  | Whole assembly;unconfirmed: for Joshua to confirm.;unconfirmed: for Joshua to confirm.;unconfirmed: for Joshua to confirm. |
| `stay-current` | stay-current: the Learning seat |  | stay-current metric (draft);unconfirmed: for Joshua to confirm.;unconfirmed: for Joshua to confirm. |
| `read-registry-freshness` | read-registry-freshness: how old is each seat's research | registry_scan | Registry freshness reading |
| `keep-it-generic` | keep-it-generic: the Character seat |  | keep-it-generic metric (draft) |
| `connect-any-integration` | connect-any-integration: the Hands seat |  | integration-added-with-zero-code (draft);unconfirmed: for Joshua to confirm. |
| `score-hub-connections` | score-hub-connections: how much of an integration is a hub connection | hub_of_hubs_scorer | Hub connection scoring |
| `card-store` | card-store: a place to keep and find cards | local_card_store | Cards found again, none lost |
| `model-call` | model-call: ask a model one question | via_call_a_model | Model call answers for the tier |
| `search-backend` | search-backend: run one web search | gemini | Search finds the source |
| `call-a-model` | call-a-model: ask a vendor's model to plan, answer or list models | multi_provider | Provider failover and vendor answers |
| `context-assembler` | context-assembler: pick the context a task needs |  | Relevant passage in the top five |

## Implementations

| Implementation | Name | Where | Sub-intent |
|---|---|---|---|
| `read-registry-freshness:registry_scan` | Registry date scan | hubofhubs/registry.py |  |
| `score-hub-connections:hub_of_hubs_scorer` | Binding scorer | hubofhubs/measure.py |  |
| `choose-a-model-tier:tier_selector` | Passing work per cost selector | hubofhubs/tiers.py |  |
| `card-store:local_card_store` | Local card store | hubofhubs/cardstore.py |  |
| `watch-for-risk:overseer` | Digest-driven overseer | hubofhubs/risk.py |  |
| `watch-for-risk:consent_gate` | Consent gate | hubofhubs/consent_gate.py |  |
| `watch-for-risk:two_stage` | Gate then overseer | hubofhubs/consent_gate.py |  |
| `search-backend:brave` | Brave Search API | hubofhubs/websearch/backends.py |  |
| `search-backend:gemini` | Gemini grounding | hubofhubs/websearch/gemini.py |  |
| `search-backend:provider` | Provider-native search | hubofhubs/websearch/backends.py |  |
| `search-backend:searxng` | SearXNG | hubofhubs/websearch/backends.py |  |
| `search-backend:serper` | Serper | hubofhubs/websearch/backends.py |  |
| `search-backend:tavily` | Tavily | hubofhubs/websearch/backends.py |  |
| `call-a-model:anthropic` | Anthropic provider | hubofhubs/models/anthropic.py |  |
| `call-a-model:deepseek` | DeepSeek provider | hubofhubs/models/openai.py |  |
| `call-a-model:gemini` | Gemini provider | hubofhubs/models/gemini.py |  |
| `call-a-model:multi_provider` | Multi-provider router | hubofhubs/models/router.py |  |
| `call-a-model:openai` | OpenAI provider | hubofhubs/models/openai.py |  |
| `context-assembler:composite` | Composite | hubofhubs/recall/composite_assembler.py |  |
| `know-the-world:web_research` | Web research | hubofhubs/websearch/research.py |  |
| `act-in-the-world:fast_edit` | One-call file edit | hubofhubs/act/fast_edit.py |  |
| `act-in-the-world:mcp_operations` | One-call MCP write | hubofhubs/act/mcp_operations.py |  |
| `know-the-world:openalex` | OpenAlex keyword search | hubofhubs/science/openalex.py |  |
| `know-the-world:openalex_semantic` | OpenAlex semantic search | hubofhubs/science/openalex_semantic.py |  |
| `know-the-world:openalex_keywords` | OpenAlex keywords, rule rewrite | hubofhubs/science/openalex_keywords.py |  |
| `know-the-world:openalex_keywords_model` | OpenAlex keywords, model rewrite | hubofhubs/science/openalex_keywords.py |  |
| `context-assembler:bm25` | BM25 over file text | hubofhubs/recall/bm25_store.py |  |
| `context-assembler:hybrid` | Hybrid fusion | hubofhubs/recall/hybrid_assembler.py |  |
| `context-assembler:vector` | Vector search | hubofhubs/recall/vector_assembler.py |  |
| `act-in-the-world:subprocess_goal_runner` | Claude Code, one shot | hubofhubs/deep/subprocess_runner.py |  |
| `act-in-the-world:stream_json_goal_runner` | Claude Code, steerable session | hubofhubs/deep/stream_runner.py |  |
| `act-in-the-world:acp_deep_runner` | Agent Client Protocol runner | hubofhubs/deep/acp_runner.py |  |
| `model-call:via_call_a_model` | Via call-a-model | hubofhubs/models/via_provider.py |  |

## Metrics

- `metric-hold-the-intents`, hold-the-intents metric (draft): `none`
- `metric-take-in-the-world`, take-in-the-world metric (draft): `none`
- `metric-remember-and-recall`, remember-and-recall metric (draft): `none`
- `metric-reason-and-answer`, reason-and-answer metric (draft): `none`
- `metric-choose-a-model-tier`, Tier choice by passing work per cost: `esoi run reason_and_answer --impl tier_selector`
- `metric-know-the-world`, Research question finds its paper: `esoi run know_the_world --impl web_research; esoi run know_the_world --impl openalex; esoi run know_the_world --impl openalex_semantic; esoi run know_the_world --impl openalex_keywords; esoi run know_the_world --impl openalex_keywords_model`
- `metric-think-critically`, think-critically metric (draft): `none`
- `metric-act-in-the-world`, Goal met by its own tests: `esoi run file_edit_goals --impl none; esoi run file_edit_goals --impl fast_edit; esoi run file_edit_goals --impl subprocess_goal_runner; esoi run file_edit_goals --impl stream_json_goal_runner; esoi run file_edit_goals --impl acp_deep_runner`
- `metric-watch-for-risk`, Risky steps stopped, ordinary steps let through: `esoi run watch_for_risk --impl overseer; esoi run watch_for_risk --impl none; esoi run watch_for_risk --impl consent_gate; esoi run watch_for_risk --impl two_stage; esoi run watch_for_risk_ambiguous --impl overseer; esoi run watch_for_risk_ambiguous --impl none; esoi run watch_for_risk_ambiguous --impl consent_gate; esoi run watch_for_risk_ambiguous --impl two_stage`
- `metric-assemble-the-whole`, Whole assembly: `none`
- `metric-stay-current`, stay-current metric (draft): `none`
- `metric-read-registry-freshness`, Registry freshness reading: `esoi run stay_current --impl registry_scan`
- `metric-keep-it-generic`, keep-it-generic metric (draft): `none`
- `metric-integration-added-with-zero-code`, integration-added-with-zero-code (draft): `none`
- `metric-score-hub-connections`, Hub connection scoring: `esoi run connect_any_integration --impl hub_of_hubs_scorer`
- `metric-integration-availability-lag`, integration-availability-lag (draft): `none`
- `metric-integration-credential-isolation`, integration-credential-isolation (draft): `none`
- `metric-tier-passing-work-per-cost`, Tier passing work per cost: `python3 -m pytest tests/test_tiers.py`
- `metric-card-store`, Cards found again, none lost: `esoi run card_store --impl local_card_store`
- `metric-model-call`, Model call answers for the tier: `esoi run model_call --impl via_call_a_model`
- `metric-search-backend`, Search finds the source: `esoi run search_backend --impl gemini; esoi run search_backend --impl provider; esoi run search_backend --impl searxng; esoi run search_backend --impl brave; esoi run search_backend --impl serper; esoi run search_backend --impl tavily`
- `metric-context-assembler`, Relevant passage in the top five: `esoi run context_assembler --impl bm25; esoi run context_assembler --impl vector; esoi run context_assembler --impl hybrid; esoi run context_assembler --impl composite; esoi run context_assembler_papers --impl bm25; esoi run context_assembler_papers --impl vector; esoi run context_assembler_papers --impl hybrid; esoi run context_assembler_papers --impl composite`
- `metric-hub-jarvis-ness`, unconfirmed: for Joshua to confirm.: `none`
- `metric-hub-jarvis-floor-consent`, unconfirmed: for Joshua to confirm.: `none`
- `metric-hub-jarvis-floor-honesty`, unconfirmed: for Joshua to confirm.: `none`
- `metric-public-stage-sourced-and-triangulated`, unconfirmed: for Joshua to confirm.: `none`
- `metric-best-in-circumstance-with-variants`, unconfirmed: for Joshua to confirm.: `none`
- `metric-guard-marginal-value-over-native-and-harness`, unconfirmed: for Joshua to confirm.: `python3 -m pytest tests/test_risk.py`
- `metric-harness-context-subagents-recursion-ranked`, unconfirmed: for Joshua to confirm.: `python3 -m pytest tests/test_deep_session_subagents.py`
- `metric-integration-served-by-combined-hubs`, unconfirmed: for Joshua to confirm.: `none`
- `metric-call-a-model`, Provider failover and vendor answers: `esoi run provider_failover --impl multi_provider; esoi run call_a_model --impl gemini; esoi run call_a_model --impl openai; esoi run call_a_model --impl deepseek`
