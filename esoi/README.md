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
| `reason-and-answer` | reason-and-answer: the Mind seat | tier_selector | reason-and-answer metric (draft);tier-passing-work-per-cost (draft) |
| `know-the-world` | know-the-world: the Science seat |  | know-the-world metric (draft) |
| `think-critically` | think-critically: the Critical thinking seat |  | think-critically metric (draft) |
| `act-in-the-world` | act-in-the-world: the Body seat |  | act-in-the-world metric (draft);unconfirmed: for Joshua to confirm. |
| `watch-for-risk` | watch-for-risk: the Overseer seat |  | watch-for-risk metric (draft);unconfirmed: for Joshua to confirm. |
| `assemble-the-whole` | assemble-the-whole: the The whole being seat |  | assemble-the-whole metric (draft);unconfirmed: for Joshua to confirm.;unconfirmed: for Joshua to confirm.;unconfirmed: for Joshua to confirm. |
| `stay-current` | stay-current: the Learning seat |  | stay-current metric (draft);unconfirmed: for Joshua to confirm.;unconfirmed: for Joshua to confirm. |
| `keep-it-generic` | keep-it-generic: the Character seat |  | keep-it-generic metric (draft) |
| `connect-any-integration` | connect-any-integration: the Hands seat |  | integration-added-with-zero-code (draft);integration-availability-lag (draft);integration-credential-isolation (draft);unconfirmed: for Joshua to confirm. |
| `card-store` | card-store: a place to keep and find cards | local_card_store | card-store metric (draft) |
| `model-call` | model-call: ask a model one question |  | model-call metric (draft) |
| `search-backend` | search-backend: run one search |  | search-backend metric (draft) |
| `call-a-model` | unconfirmed: for Joshua to confirm. |  | model-call metric (draft) |
| `context-assembler` | unconfirmed: for Joshua to confirm. |  | unconfirmed: for Joshua to confirm. |

## Implementations

| Implementation | Name | Where | Sub-intent |
|---|---|---|---|
| `stay-current:registry_scan` | Registry freshness reading | hubofhubs/registry.py |  |
| `connect-any-integration:hub_of_hubs_scorer` | Hub-of-hubs scorer | hubofhubs/measure.py |  |
| `reason-and-answer:tier_selector` | Tier selector | hubofhubs/tiers.py |  |
| `card-store:local_card_store` | Local card store | hubofhubs/cardstore.py |  |
| `watch-for-risk:overseer` | Digest-driven overseer | hubofhubs/risk.py |  |
| `search-backend:brave` | Brave Search API backend | hubofhubs/websearch/backends.py |  |
| `search-backend:gemini` | Gemini grounding backend | hubofhubs/websearch/gemini.py |  |
| `search-backend:provider` | Provider-native backend | hubofhubs/websearch/backends.py |  |
| `search-backend:searxng` | SearXNG backend | hubofhubs/websearch/backends.py |  |
| `search-backend:serper` | Serper backend | hubofhubs/websearch/backends.py |  |
| `search-backend:tavily` | Tavily backend | hubofhubs/websearch/backends.py |  |
| `call-a-model:anthropic` | unconfirmed: for Joshua to confirm. | hubofhubs/models/anthropic.py |  |
| `call-a-model:deepseek` | unconfirmed: for Joshua to confirm. | hubofhubs/models/openai.py |  |
| `call-a-model:gemini` | unconfirmed: for Joshua to confirm. | hubofhubs/models/gemini.py |  |
| `call-a-model:multi_provider` | unconfirmed: for Joshua to confirm. | hubofhubs/models/router.py |  |
| `call-a-model:openai` | unconfirmed: for Joshua to confirm. | hubofhubs/models/openai.py |  |
| `context-assembler:composite` | unconfirmed: for Joshua to confirm. | hubofhubs/recall/composite_assembler.py |  |
| `know-the-world:web_research` | unconfirmed: for Joshua to confirm. | hubofhubs/websearch/research.py |  |
| `act-in-the-world:fast_edit` | unconfirmed: for Joshua to confirm. | hubofhubs/act/fast_edit.py |  |
| `act-in-the-world:mcp_operations` | unconfirmed: for Joshua to confirm. | hubofhubs/act/mcp_operations.py |  |
| `know-the-world:openalex` | unconfirmed: for Joshua to confirm. | hubofhubs/science/openalex.py |  |
| `context-assembler:bm25` | unconfirmed: for Joshua to confirm. | hubofhubs/recall/bm25_store.py |  |
| `context-assembler:hybrid` | unconfirmed: for Joshua to confirm. | hubofhubs/recall/hybrid_assembler.py |  |
| `context-assembler:vector` | unconfirmed: for Joshua to confirm. | hubofhubs/recall/vector_assembler.py |  |
| `act-in-the-world:subprocess_goal_runner` | unconfirmed: for Joshua to confirm. | hubofhubs/deep/subprocess_runner.py |  |
| `act-in-the-world:stream_json_goal_runner` | unconfirmed: for Joshua to confirm. | hubofhubs/deep/stream_runner.py |  |
| `act-in-the-world:acp_deep_runner` | unconfirmed: for Joshua to confirm. | hubofhubs/deep/acp_runner.py |  |

## Metrics

- `metric-hold-the-intents`, hold-the-intents metric (draft): `none`
- `metric-take-in-the-world`, take-in-the-world metric (draft): `none`
- `metric-remember-and-recall`, remember-and-recall metric (draft): `none`
- `metric-reason-and-answer`, reason-and-answer metric (draft): `none`
- `metric-know-the-world`, know-the-world metric (draft): `none`
- `metric-think-critically`, think-critically metric (draft): `none`
- `metric-act-in-the-world`, act-in-the-world metric (draft): `none`
- `metric-watch-for-risk`, watch-for-risk metric (draft): `none`
- `metric-assemble-the-whole`, assemble-the-whole metric (draft): `none`
- `metric-stay-current`, stay-current metric (draft): `none`
- `metric-keep-it-generic`, keep-it-generic metric (draft): `none`
- `metric-integration-added-with-zero-code`, integration-added-with-zero-code (draft): `none`
- `metric-integration-availability-lag`, integration-availability-lag (draft): `none`
- `metric-integration-credential-isolation`, integration-credential-isolation (draft): `none`
- `metric-tier-passing-work-per-cost`, tier-passing-work-per-cost (draft): `python3 -m pytest tests/test_tiers.py`
- `metric-card-store`, card-store metric (draft): `none`
- `metric-model-call`, model-call metric (draft): `none`
- `metric-search-backend`, search-backend metric (draft): `none`
- `metric-context-assembler`, unconfirmed: for Joshua to confirm.: `none`
- `metric-hub-jarvis-ness`, unconfirmed: for Joshua to confirm.: `none`
- `metric-hub-jarvis-floor-consent`, unconfirmed: for Joshua to confirm.: `none`
- `metric-hub-jarvis-floor-honesty`, unconfirmed: for Joshua to confirm.: `none`
- `metric-public-stage-sourced-and-triangulated`, unconfirmed: for Joshua to confirm.: `none`
- `metric-best-in-circumstance-with-variants`, unconfirmed: for Joshua to confirm.: `none`
- `metric-guard-marginal-value-over-native-and-harness`, unconfirmed: for Joshua to confirm.: `none`
- `metric-harness-context-subagents-recursion-ranked`, unconfirmed: for Joshua to confirm.: `none`
- `metric-integration-served-by-combined-hubs`, unconfirmed: for Joshua to confirm.: `none`
