# hubofhubs

*ESOI records kept beside the code in `hubofhubs`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

## take-in-the-world: the World seat (`take-in-the-world`)

Connect any AI to tools, search and data sources without writing code for each one.

- Entry call: `hubofhubs.run("take-in-the-world", 'latest Rust release')`
- Selected implementation: `search_backends`
- Metric: take-in-the-world metric (draft)
- Implemented by: [`hubofhubs/areas.py`](areas.py), [`hubofhubs/terminal/__init__.py`](terminal/__init__.py), [`hubofhubs/terminal/asks.py`](terminal/asks.py), [`hubofhubs/terminal/blocks.py`](terminal/blocks.py), [`hubofhubs/terminal/render.py`](terminal/render.py), [`hubofhubs/terminal/stopped.py`](terminal/stopped.py), [`hubofhubs/terminal/strings.py`](terminal/strings.py), [`hubofhubs/terminal/trail.py`](terminal/trail.py) and 3 more

## reason-and-answer: the Mind seat (`reason-and-answer`)

Reason to a good answer at the lowest cost that still passes, for any product that needs an AI that plans and answers.

- Entry call: `hubofhubs.run("reason-and-answer", ...)`
- Selected implementation: `model_calls`
- Metric: reason-and-answer metric (draft)
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../docs/reference/work-trace-event.schema.json), [`hubofhubs/areas.py`](areas.py), [`hubofhubs/models/__init__.py`](models/__init__.py), [`hubofhubs/models/anthropic.py`](models/anthropic.py), [`hubofhubs/models/claude_cli.py`](models/claude_cli.py), [`hubofhubs/models/family.py`](models/family.py), [`hubofhubs/models/gemini.py`](models/gemini.py), [`hubofhubs/models/layers.py`](models/layers.py) and 46 more

## choose-a-model-tier: pick the model for each tier (`choose-a-model-tier`)

Choose the cheapest model that does the job at each tier, for any product that calls models.

- Entry call: `hubofhubs.run("choose-a-model-tier", {'available': ['anthropic']})`
- Selected implementation: `tier_selector`
- Metric: Tier choice by passing work per cost, Tier passing work per cost
- Implemented by: [`.env.example`](../.env.example), [`hubofhubs/__init__.py`](__init__.py), [`hubofhubs/areas.py`](areas.py), [`hubofhubs/arm_needs.py`](arm_needs.py), [`hubofhubs/binding.py`](binding.py), [`hubofhubs/card.py`](card.py), [`hubofhubs/cardstore.py`](cardstore.py), [`hubofhubs/cases.py`](cases.py) and 41 more

## know-the-world: the Science seat (`know-the-world`)

Support claims with sources a reader can check, for anyone who asks an AI a factual or research question.

- Entry call: `hubofhubs.run("know-the-world", 'meditation and attention')`
- Selected implementation: `openalex_semantic`
- Metric: Research question finds its paper
- Implemented by: [`hubofhubs/science/__init__.py`](science/__init__.py), [`hubofhubs/science/citations.py`](science/citations.py), [`hubofhubs/science/crossref.py`](science/crossref.py), [`hubofhubs/science/openalex.py`](science/openalex.py), [`hubofhubs/science/openalex_keywords.py`](science/openalex_keywords.py), [`hubofhubs/science/openalex_semantic.py`](science/openalex_semantic.py), [`hubofhubs/science/openalex_semantic_and_web.py`](science/openalex_semantic_and_web.py), [`hubofhubs/science/transport.py`](science/transport.py) and 8 more

## act-in-the-world: the Body seat (`act-in-the-world`)

Make intended changes in the world and no unrequested ones, for any product that lets an AI act.

- Entry call: `hubofhubs.run("act-in-the-world", ...)`
- Selected implementation: `fast_edit`
- Metric: Goal met by its own tests, Harness, context, sub-agents and recursion ranked
- Implemented by: [`hubofhubs/act/__init__.py`](act/__init__.py), [`hubofhubs/act/editblock.py`](act/editblock.py), [`hubofhubs/act/execution_record.py`](act/execution_record.py), [`hubofhubs/act/fast_edit.py`](act/fast_edit.py), [`hubofhubs/act/folder_writer.py`](act/folder_writer.py), [`hubofhubs/act/mcp_client.py`](act/mcp_client.py), [`hubofhubs/act/mcp_operations.py`](act/mcp_operations.py), [`hubofhubs/act/secret_redaction.py`](act/secret_redaction.py) and 30 more

## watch-for-risk: the Overseer seat (`watch-for-risk`)

Stop irreversible or human-only steps before they happen, without slowing ordinary work, for any product that lets an AI act.

- Entry call: `hubofhubs.run("watch-for-risk", 'delete the old backup folder')`
- Selected implementation: `consent_gate`
- Metric: Risky steps stopped, ordinary steps let through, Guard marginal value
- Implemented by: [`.env.example`](../.env.example), [`hubofhubs/__init__.py`](__init__.py), [`hubofhubs/areas.py`](areas.py), [`hubofhubs/arm_needs.py`](arm_needs.py), [`hubofhubs/binding.py`](binding.py), [`hubofhubs/card.py`](card.py), [`hubofhubs/cardstore.py`](cardstore.py), [`hubofhubs/cases.py`](cases.py) and 41 more

## assemble-the-whole: the The whole being seat (`assemble-the-whole`)

Give any consumer a working system from one line of configuration.

- Entry call: `hubofhubs.run("assemble-the-whole", 'what is the latest Rust release?')`
- Selected implementation: `zero_config`
- Metric: Whole assembly, Capability of the whole from the user's seat, Consent floor, Honesty floor
- Implemented by: [`.gitignore`](../.gitignore), [`CHANGELOG.md`](../CHANGELOG.md), [`CLAUDE.md`](../CLAUDE.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`LICENSE`](../LICENSE), [`NOTICE`](../NOTICE), [`esoi.toml`](../esoi.toml), [`esoi/COMPONENTS.md`](../esoi/COMPONENTS.md) and 152 more

## stay-current: the Learning seat (`stay-current`)

Keep every seat's candidates current for anyone who relies on the hub.

- Entry call: `hubofhubs.run("stay-current", '2026-11-03')`
- Selected implementation: `registry_research`
- Metric: stay-current metric (draft), Public stage sourced and triangulated, Best in circumstance with variants
- Implemented by: [`hubofhubs/areas.py`](areas.py)

## read-registry-freshness: how old is each seat's research (`read-registry-freshness`)

Show maintainers which parts of the hub have gone stale.

- Entry call: `hubofhubs.run("read-registry-freshness", '2026-10-01')`
- Selected implementation: `registry_scan`
- Metric: Registry freshness reading
- Implemented by: [`.env.example`](../.env.example), [`docs/explanation/compared.md`](../docs/explanation/compared.md), [`docs/explanation/glossary.md`](../docs/explanation/glossary.md), [`docs/explanation/how-we-measure.md`](../docs/explanation/how-we-measure.md), [`docs/explanation/public-evidence.md`](../docs/explanation/public-evidence.md), [`docs/explanation/resolution-design.md`](../docs/explanation/resolution-design.md), [`docs/explanation/science-search.md`](../docs/explanation/science-search.md), [`docs/explanation/terminal-harness.md`](../docs/explanation/terminal-harness.md) and 94 more

## keep-it-generic: the Character seat (`keep-it-generic`)

Keep the hub usable by any consumer, with no wording or settings of one product in it.

- Entry call: `hubofhubs.run("keep-it-generic", ['examplevendor'])`
- Selected implementation: `prompts_as_data`
- Metric: keep-it-generic metric (draft), Intents whose solutions one paragraph and one diagram explain as the code builds them
- Implemented by: [`hubofhubs/areas.py`](areas.py)

## connect-any-integration: the Hands seat (`connect-any-integration`)

Let users connect the apps they use with zero code per integration, for any product built on the hub.

- Entry call: `hubofhubs.run("connect-any-integration", 'web_search')`
- Selected implementation: `catalog_entries`
- Metric: integration-added-with-zero-code (draft), Integration served by combined hubs
- Implemented by: [`hubofhubs/areas.py`](areas.py)

## score-hub-connections: how much of an integration is a hub connection (`score-hub-connections`)

Show a consumer how much of its integration is a hub connection and how much is hand-wired.

- Entry call: `hubofhubs.run("score-hub-connections", {'facts': {}, 'connections': []})`
- Selected implementation: `hub_of_hubs_scorer`
- Metric: Hub connection scoring
- Implemented by: [`.env.example`](../.env.example), [`docs/explanation/compared.md`](../docs/explanation/compared.md), [`docs/explanation/glossary.md`](../docs/explanation/glossary.md), [`docs/explanation/how-we-measure.md`](../docs/explanation/how-we-measure.md), [`docs/explanation/public-evidence.md`](../docs/explanation/public-evidence.md), [`docs/explanation/resolution-design.md`](../docs/explanation/resolution-design.md), [`docs/explanation/science-search.md`](../docs/explanation/science-search.md), [`docs/explanation/terminal-harness.md`](../docs/explanation/terminal-harness.md) and 86 more

## card-store: a place to keep and find cards (`card-store`)

Keep and find cards for any consumer, with no service to run.

- Entry call: `hubofhubs.run("card-store", 'rust release')`
- Selected implementation: `local_card_store`
- Metric: Cards found again, none lost
- Implemented by: [`.env.example`](../.env.example), [`hubofhubs/__init__.py`](__init__.py), [`hubofhubs/areas.py`](areas.py), [`hubofhubs/arm_needs.py`](arm_needs.py), [`hubofhubs/binding.py`](binding.py), [`hubofhubs/card.py`](card.py), [`hubofhubs/cardstore.py`](cardstore.py), [`hubofhubs/cases.py`](cases.py) and 41 more

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["take-in-the-world: the World seat<br/>take-in-the-world"]
    s1["reason-and-answer: the Mind seat<br/>reason-and-answer"]
    s2["choose-a-model-tier: pick the model for...<br/>choose-a-model-tier"]
    s3["know-the-world: the Science seat<br/>know-the-world"]
    s4["act-in-the-world: the Body seat<br/>act-in-the-world"]
    s5["watch-for-risk: the Overseer seat<br/>watch-for-risk"]
    s6["assemble-the-whole: the The whole being...<br/>assemble-the-whole"]
    s7["stay-current: the Learning seat<br/>stay-current"]
    s8["read-registry-freshness: how old is...<br/>read-registry-freshness"]
    s9["keep-it-generic: the Character seat<br/>keep-it-generic"]
    s10["connect-any-integration: the Hands seat<br/>connect-any-integration"]
    s11["score-hub-connections: how much of an...<br/>score-hub-connections"]
    s12["card-store: a place to keep and find...<br/>card-store"]
    s13["think-critically: the Critical thinking...<br/>think-critically"]
    s14["model-call: ask a model one question<br/>model-call"]
    s15["call-a-model: ask a vendor's model to...<br/>call-a-model"]
    s16["remember-and-recall: the Subconscious...<br/>remember-and-recall"]
    s17["context-assembler: pick the context a...<br/>context-assembler"]
    s18["cards-from-files: cards for a folder<br/>cards-from-files"]
    s19["search-backend: run one web search<br/>search-backend"]
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
    s16 -->|"The cards a task needs, in one rendered view with their ids"| s6
    s17 -->|"An assembled context view and the ids of the cards it drew..."| s16
    s18 -->|"Cards in the card-store record shape (grouping, summary..."| s16
    s19 -->|"A response of hits (title, link, snippet, date, passages..."| s0
    s19 -->|"A response of hits (title, link, snippet, date, passages..."| s3
```

## Implementations

| Implementation | Name | Code | Selected |
|---|---|---|---|
| `read-registry-freshness:registry_scan` | Registry date scan | [`hubofhubs/registry.py`](registry.py) | selected |
| `score-hub-connections:hub_of_hubs_scorer` | Binding scorer | [`hubofhubs/measure.py`](measure.py) | selected |
| `choose-a-model-tier:tier_selector` | Passing work per cost selector | [`hubofhubs/tiers.py`](tiers.py) | selected |
| `card-store:local_card_store` | Local card store | [`hubofhubs/cardstore.py`](cardstore.py) | selected |
| `watch-for-risk:overseer` | Digest-driven overseer | [`hubofhubs/risk.py`](risk.py) |  |
| `watch-for-risk:consent_gate` | Consent gate | [`hubofhubs/consent_gate.py`](consent_gate.py) | selected |
| `watch-for-risk:two_stage` | Gate then overseer | [`hubofhubs/consent_gate.py`](consent_gate.py) |  |
| `assemble-the-whole:zero_config` | One-call assembly of the whole hub | [`hubofhubs/whole.py`](whole.py) | selected |
| `take-in-the-world:search_backends` | Search and papers as the way in | [`hubofhubs/areas.py`](areas.py) | selected |
| `reason-and-answer:model_calls` | Answers through the measured model for the tier | [`hubofhubs/areas.py`](areas.py) | selected |
| `keep-it-generic:prompts_as_data` | Audit of vendor wording, staleness and configuration | [`hubofhubs/areas.py`](areas.py) | selected |
| `stay-current:registry_research` | Stale areas from the registry dates | [`hubofhubs/areas.py`](areas.py) | selected |
| `connect-any-integration:catalog_entries` | Share of connections that need no code | [`hubofhubs/areas.py`](areas.py) | selected |

## Metrics

- `metric-take-in-the-world`, take-in-the-world metric (draft)
- `metric-reason-and-answer`, reason-and-answer metric (draft)
- `metric-choose-a-model-tier`, Tier choice by passing work per cost: leader `tier_selector`, 36 of 36 cases
- `metric-know-the-world`, Research question finds its paper: leader `openalex_semantic`, 52 of 150 cases
- `metric-act-in-the-world`, Goal met by its own tests: leader `fast_edit`, 29 of 30 cases
- `metric-watch-for-risk`, Risky steps stopped, ordinary steps let through: leader `consent_gate`, 36 of 36 cases
- `metric-assemble-the-whole`, Whole assembly
- `metric-stay-current`, stay-current metric (draft)
- `metric-read-registry-freshness`, Registry freshness reading: leader `registry_scan`, 41 of 41 cases
- `metric-keep-it-generic`, keep-it-generic metric (draft)
- `metric-integration-added-with-zero-code`, integration-added-with-zero-code (draft)
- `metric-score-hub-connections`, Hub connection scoring: leader `hub_of_hubs_scorer`, 33 of 33 cases
- `metric-integration-availability-lag`, integration-availability-lag (draft)
- `metric-integration-credential-isolation`, integration-credential-isolation (draft)
- `metric-tier-passing-work-per-cost`, Tier passing work per cost
- `metric-card-store`, Cards found again, none lost: leader `local_card_store`, 35 of 35 cases
- `metric-hub-jarvis-ness`, Capability of the whole from the user's seat
- `metric-hub-jarvis-floor-consent`, Consent floor
- `metric-hub-jarvis-floor-honesty`, Honesty floor
- `metric-public-stage-sourced-and-triangulated`, Public stage sourced and triangulated
- `metric-best-in-circumstance-with-variants`, Best in circumstance with variants
- `metric-guard-marginal-value-over-native-and-harness`, Guard marginal value
- `metric-harness-context-subagents-recursion-ranked`, Harness, context, sub-agents and recursion ranked
- `metric-integration-served-by-combined-hubs`, Integration served by combined hubs
- `metric-solution-coherence`, Intents whose solutions one paragraph and one diagram explain as the code builds them

## Problems

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
- `hprob-addon-guard-without-marginal-value`: A guard or reviewer added around a model or harness is kept because it sounds careful, without showing that it catches anything the model or harness would not catch alone.
- `hprob-harness-dear-and-slow-on-the-subscription`: An agent harness used on a flat subscription is slow and spends more tokens than the work needs, partly because the context it is given is poor and partly because it repeats work through sub-agents...
- `hprob-one-integration-needs-several-hubs`: One app connection (a calendar, a drive, a chat) is served better by several hubs combined than by any one, but a product wires a single hub and hand-writes the rest.

## Ideals

- `HI1`: Each seat holds the part that measures best on shared cases.
- `HI2`: Configuration in, working system out, no glue code.
- `HI3`: No area goes a week without a fresh search and comparison.
- `HI4`: Any part can be replaced by configuration when another measures better or fails.
- `HI5`: The assembled system is tested end to end on a production consumer, not only part by part.
- `HI6`: No consumer-specific content.
- `hideal-jarvis-from-the-users-seat`: The assembled hub is judged as the user meets it: one capable assistant that gets real work done, asks before it does anything that cannot be undone, and reports only what it did.
- `hideal-common-sense-metrics-with-sourced-stages`: Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- `hideal-best-in-circumstance-with-variants`: The hub names the best part for each circumstance and not one winner, by comparing variants of a part (one setting changed) on the same cases.
- `hideal-guards-earn-their-place`: A guard is kept only when it catches something the model or harness would miss, shown by running the same cases with and without it.
- `hideal-cheap-fast-harness-with-ideal-context`: An agent harness is chosen for the lowest cost and time at the same pass rate, given the best context the hub can assemble for it, and the choice accounts for sub-agents and recursion.
- `hideal-hubs-combined-per-integration`: An integration is served by the combination of hubs that covers the most of it, chosen by data and never by one hub's reach.

## Where to go next

- Intent: [The best parts for AI intelligence, assembled and proven](../esoi/README.md)
- Down: [hubofhubs/act](act/README.md)
- Down: [hubofhubs/critique](critique/README.md)
- Down: [hubofhubs/deep](deep/README.md)
- Down: [hubofhubs/models](models/README.md)
- Down: [hubofhubs/recall](recall/README.md)
- Down: [hubofhubs/science](science/README.md)
- Down: [hubofhubs/websearch](websearch/README.md)
- Repository: [top README](../README.md)
