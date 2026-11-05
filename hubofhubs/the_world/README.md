# Awareness of the outside and interaction with it

The AI knows what is outside the system and can interact with it: it brings in knowledge a reader can check, uses the right tool for each kind of need, asks a model through one measured path and keeps its own research current.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-world:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: Tool categories as solutions, with integrations as their implementations, go beyond bringing in a web search, and a category can gain a better integration without any product rewriting its code. The models the hub asks and the freshness of its research change with the outside too.

## How the solutions fit together

World is how the system learns what is outside it and acts on it. Science returns observations of public research that a reader can cite. Tools lets the AI use the tool of a category through Web Search, File Reading, File Editing, Connected System Operations or Delegated Agent Sessions, and refuses a category the authority does not allow. File Editing makes its one-call edit through Vendor Model Caller at the tier that Model Tier Chooser picks. Model Plumbing is how every part asks a model, through Model Tier Chooser and Vendor Model Caller. Vendor Model Caller steps to the next provider when one fails. Learning keeps the research current by reading dates through Research Freshness Reader.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Vendor Model Caller<br/><i>vendor-model-caller</i>"]
    s1["Model Tier Chooser<br/><i>model-tier-chooser</i>"]
    s2["Model Plumbing<br/><i>model-plumbing</i>"]
    s3["Learning<br/><i>the-learning</i>"]
    s4["Research Freshness Reader<br/><i>research-freshness-reader</i>"]
    s5["Science<br/><i>the-science</i>"]
    s6["Web Search<br/><i>web-search</i>"]
    s7["Tools<br/><i>the-tools</i>"]
    s8["File Editing<br/><i>file-editing</i>"]
    s9["Connected System Operations<br/><i>connected-system-operations</i>"]
    s10["Delegated Agent Sessions<br/><i>delegated-agent-sessions</i>"]
    s11["File Reading<br/><i>read-files</i>"]
    s0 -->|"Text, a plan or a list of models"| s2
    s0 -->|"Text, a plan or a list of models"| s8
    s1 -->|"A mapping from each tier to the chosen provider and model"| s2
    s1 -->|"A mapping from each tier to the chosen provider and model"| s8
    s2 -->|"The model's answer to a prompt at a tier"| s5
    s4 -->|"Days since the date, or the combined freshness reading with..."| s3
    s6 -->|"A response of hits (title, link, snippet, date, passages..."| s5
    s6 -->|"A response of hits (title, link, snippet, date, passages..."| s7
    s8 -->|"A report of the file change, or the reason it was declined..."| s7
    s9 -->|"The result of the operation, or the reason it was declined"| s7
    s10 -->|"A result that says whether the goal was met, with the..."| s7
    s11 -->|"The file paths of a folder, and the text of the files asked..."| s7
```

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Vendor Model Caller | `vendor-model-caller` | `hubofhubs.run("vendor-model-caller", ...)` | Claude Code CLI (`claude_cli`) | Provider failover |
| Model Tier Chooser | `model-tier-chooser` | `hubofhubs.run("model-tier-chooser", {'available': ['anthropic']})` | Passing work per cost selector (`tier_selector`) | Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer |
| Model Plumbing | `model-plumbing` | `hubofhubs.run("model-plumbing", ...)` | Tier chooser then vendor (`via_vendor`) | Model asked at the tier, within the budget |
| Learning | `the-learning` | `hubofhubs.run("the-learning", '2026-11-03')` | Stale areas from the registry dates (`registry_research`) | Days since each seat was researched, Public stage sourced and triangulated, Best in circumstance with variants |
| Research Freshness Reader | `research-freshness-reader` | `hubofhubs.run("research-freshness-reader", '2026-10-01')` | Registry date scan (`registry_scan`) | Registry freshness reading |
| Science | `the-science` | `hubofhubs.run("the-science", 'meditation and attention')` | OpenAlex semantic search (`openalex_semantic`) | Research question finds its paper |
| Web Search | `web-search` | `hubofhubs.run("web-search", 'latest Rust release')` | Gemini grounding (`gemini`) | Search finds the source |
| Tools | `the-tools` | `hubofhubs.run("the-tools", ...)` | Categories of tools (`composition`) | The best integration of each category is chosen, Share of connections that need no code, Share of connections that need no code |
| File Editing | `file-editing` | `hubofhubs.run("file-editing", ...)` | One-call file edit (`fast_edit`) | Goal met by its own tests |
| Connected System Operations | `connected-system-operations` | `hubofhubs.run("connected-system-operations", ...)` | none selected | The operation is carried out and nothing else |
| Delegated Agent Sessions | `delegated-agent-sessions` | `hubofhubs.run("delegated-agent-sessions", ...)` | Claude Code, steerable session (`stream_json_goal_runner`) | Harness, context, sub-agents and recursion ranked, Goal met by its own tests (agent sessions) |
| File Reading | `read-files` | `hubofhubs.run("read-files", {'root': '.', 'paths': []})` | Folder reader (`folder_reader`) | Files read inside the folder |

## Problems and ideals

**Problems**

- Every part picks its own model (`hprob-every-part-picks-its-own-model`): Each part that needs a model chooses and calls it its own way, so tier choice, cost and failover are repeated and drift apart.
- One public benchmark trusted alone (`hprob-public-evals-relied-on-singly`): One public benchmark is trusted alone to rank parts, although it may measure a different task, be saturated or leaked into training data, and its source is rarely checked.
- Best pick ignores circumstance (`hprob-one-best-pick-ignores-circumstance`): A part is ranked best overall, but which part is best depends on the circumstance (a cost limit, a speed limit, a language, the size of the input), so the single winner is wrong for many users.
- Harness dear and slow on a subscription (`hprob-harness-dear-and-slow-on-the-subscription`): An agent harness used on a flat subscription is slow and spends more tokens than the work needs, partly because the context it is given is poor and partly because it repeats work through sub-agents...
- Every product wires its own tools (`hprob-each-product-wires-its-own-tools`): Each product wires its own integrations and finds a person's data its own way, so a new kind of integration means new code and a person's data locations are asked for again by every product.
- Claims without checkable sources (`hprob-claims-without-checkable-sources`): A factual or research answer cites a web page instead of the papers and data that bear on it, so the reader cannot check it.
- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.
- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Every connected system's operations are wired into each product by hand.
- Research dates read by hand (`hprob-research-dates-are-read-by-hand`): How old each area's research is has to be worked out by hand, so stale recommendations go unnoticed.

**Ideals**

- Tools chosen by category (`hideal-tools-chosen-by-category`): For each category of tool, the best integration is chosen by measurement, and a person's data locations are declared once.

## Metrics and their leaders

- Tier choice by passing work per cost (`metric-model-tier-chooser`): leader `tier_selector`, 36 of 36 cases
- Tier passing work per cost (`metric-tier-passing-work-per-cost`)
- Model quality on hard maths (`metric-model-quality`): leader `deepseek_v4_pro`, 3 of 3 cases
- Vendor arms answer (`metric-vendor-answers`): leader `claude_cli`, 3 of 3 cases
- Provider failover (`metric-vendor-model-caller`): leader `multi_provider`, 30 of 30 cases
- Model asked at the tier, within the budget (`metric-model-plumbing`): leader `via_vendor`, 30 of 30 cases
- Days since each seat was researched (`metric-the-learning`)
- Registry freshness reading (`metric-research-freshness-reader`): leader `registry_scan`, 41 of 41 cases
- Public stage sourced and triangulated (`metric-public-stage-sourced-and-triangulated`)
- Best in circumstance with variants (`metric-best-in-circumstance-with-variants`)
- and 9 more: all 19 are in [metrics](#metrics) of the full record below

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- Every part picks its own model (`hprob-every-part-picks-its-own-model`): Each part that needs a model chooses and calls it its own way, so tier choice, cost and failover are repeated and drift apart.
- One public benchmark trusted alone (`hprob-public-evals-relied-on-singly`): One public benchmark is trusted alone to rank parts, although it may measure a different task, be saturated or leaked into training data, and its source is rarely checked.
- Best pick ignores circumstance (`hprob-one-best-pick-ignores-circumstance`): A part is ranked best overall, but which part is best depends on the circumstance (a cost limit, a speed limit, a language, the size of the input), so the single winner is wrong for many users.
- Harness dear and slow on a subscription (`hprob-harness-dear-and-slow-on-the-subscription`): An agent harness used on a flat subscription is slow and spends more tokens than the work needs, partly because the context it is given is poor and partly because it repeats work through sub-agents and recursion.
- Every product wires its own tools (`hprob-each-product-wires-its-own-tools`): Each product wires its own integrations and finds a person's data its own way, so a new kind of integration means new code and a person's data locations are asked for again by every product.
- Claims without checkable sources (`hprob-claims-without-checkable-sources`): A factual or research answer cites a web page instead of the papers and data that bear on it, so the reader cannot check it.
- Small edits pay for an agent (`hprob-small-edits-pay-for-an-agent`): A change to one file is routed to an agent session that costs and takes far more than the edit needs, or is hand-written for each product.
- System operations wired by hand (`hprob-each-system-operation-is-wired-by-hand`): Every connected system's operations are wired into each product by hand.
- Research dates read by hand (`hprob-research-dates-are-read-by-hand`): How old each area's research is has to be worked out by hand, so stale recommendations go unnoticed.

### Ideals

- Tools chosen by category (`hideal-tools-chosen-by-category`): For each category of tool, the best integration is chosen by measurement, and a person's data locations are declared once.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Vendor Model Caller | `vendor-model-caller` | Claude Code CLI (`claude_cli`) | Provider failover |
| Model Tier Chooser | `model-tier-chooser` | Passing work per cost selector (`tier_selector`) | Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer |
| Model Plumbing | `model-plumbing` | Tier chooser then vendor (`via_vendor`) | Model asked at the tier, within the budget |
| Learning | `the-learning` | Stale areas from the registry dates (`registry_research`) | Days since each seat was researched, Public stage sourced and triangulated, Best in circumstance with variants |
| Research Freshness Reader | `research-freshness-reader` | Registry date scan (`registry_scan`) | Registry freshness reading |
| Science | `the-science` | OpenAlex semantic search (`openalex_semantic`) | Research question finds its paper |
| Web Search | `web-search` | Gemini grounding (`gemini`) | Search finds the source |
| Tools | `the-tools` | Categories of tools (`composition`) | The best integration of each category is chosen, Share of connections that need no code, Share of connections that need no code |
| File Editing | `file-editing` | One-call file edit (`fast_edit`) | Goal met by its own tests |
| Connected System Operations | `connected-system-operations` | none selected | The operation is carried out and nothing else |
| Delegated Agent Sessions | `delegated-agent-sessions` | Claude Code, steerable session (`stream_json_goal_runner`) | Harness, context, sub-agents and recursion ranked, Goal met by its own tests (agent sessions) |
| File Reading | `read-files` | Folder reader (`folder_reader`) | Files read inside the folder |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Passing work per cost selector | `model-tier-chooser:tier_selector` | [hubofhubs/tiers.py](../tiers.py) |  |
| Anthropic provider | `vendor-model-caller:anthropic` | [hubofhubs/models/anthropic.py](../models/anthropic.py) |  |
| DeepSeek provider | `vendor-model-caller:deepseek` | [hubofhubs/models/openai.py](../models/openai.py) |  |
| Gemini provider | `vendor-model-caller:gemini` | [hubofhubs/models/gemini.py](../models/gemini.py) |  |
| Multi-provider router | `vendor-model-caller:multi_provider` | [hubofhubs/models/router.py](../models/router.py) |  |
| OpenAI provider | `vendor-model-caller:openai` | [hubofhubs/models/openai.py](../models/openai.py) |  |
| Claude Code CLI | `vendor-model-caller:claude_cli` | [hubofhubs/models/claude_cli.py](../models/claude_cli.py) |  |
| One-call file edit | `file-editing:fast_edit` | [hubofhubs/act/fast_edit.py](../act/fast_edit.py) |  |
| One-call MCP write | `connected-system-operations:mcp_operations` | [hubofhubs/act/mcp_operations.py](../act/mcp_operations.py) |  |
| Claude Code, one shot | `delegated-agent-sessions:subprocess_goal_runner` | [hubofhubs/deep/subprocess_runner.py](../deep/subprocess_runner.py) |  |
| Claude Code, steerable session | `delegated-agent-sessions:stream_json_goal_runner` | [hubofhubs/deep/stream_runner.py](../deep/stream_runner.py) |  |
| Agent Client Protocol runner | `delegated-agent-sessions:acp_deep_runner` | [hubofhubs/deep/acp_runner.py](../deep/acp_runner.py) |  |
| Registry date scan | `research-freshness-reader:registry_scan` | [hubofhubs/registry.py](../registry.py) |  |
| Stale areas from the registry dates | `the-learning:registry_research` | [hubofhubs/areas.py](../areas.py) |  |
| OpenAlex keyword search | `the-science:openalex` | [hubofhubs/science/openalex.py](../science/openalex.py) |  |
| OpenAlex semantic search | `the-science:openalex_semantic` | [hubofhubs/science/openalex_semantic.py](../science/openalex_semantic.py) |  |
| OpenAlex keywords, rule rewrite | `the-science:openalex_keywords` | [hubofhubs/science/openalex_keywords.py](../science/openalex_keywords.py) |  |
| OpenAlex keywords, model rewrite | `the-science:openalex_keywords_model` | [hubofhubs/science/openalex_keywords.py](../science/openalex_keywords.py) |  |
| Semantic and web paper search | `the-science:openalex_semantic_and_web` | [hubofhubs/science/openalex_semantic_and_web.py](../science/openalex_semantic_and_web.py) |  |
| Brave Search API | `web-search:brave` | [hubofhubs/websearch/backends.py](../websearch/backends.py) |  |
| Gemini grounding | `web-search:gemini` | [hubofhubs/websearch/gemini.py](../websearch/gemini.py) |  |
| Provider-native search | `web-search:provider` | [hubofhubs/websearch/backends.py](../websearch/backends.py) |  |
| SearXNG metasearch | `web-search:searxng` | [hubofhubs/websearch/backends.py](../websearch/backends.py) |  |
| Serper Google search | `web-search:serper` | [hubofhubs/websearch/backends.py](../websearch/backends.py) |  |
| Tavily search API | `web-search:tavily` | [hubofhubs/websearch/backends.py](../websearch/backends.py) |  |
| Web research | `the-science:web_research` | [hubofhubs/websearch/research.py](../websearch/research.py) |  |
| Categories of tools | `the-tools:composition` | [hubofhubs/flows.py](../flows.py) |  |
| Tier chooser then vendor | `model-plumbing:via_vendor` | [hubofhubs/models/via_provider.py](../models/via_provider.py) |  |
| Folder reader | `read-files:folder_reader` | [hubofhubs/act/read_files.py](../act/read_files.py) |  |

### Metrics

- Tier choice by passing work per cost (`metric-model-tier-chooser`): `esoi run reason_and_answer --impl tier_selector`
- Tier passing work per cost (`metric-tier-passing-work-per-cost`): `python3 -m pytest tests/test_tiers.py`
- Model quality on hard maths (`metric-model-quality`): `esoi run model_quality_aime --impl claude_haiku; esoi run model_quality_aime --impl claude_sonnet; esoi run model_quality_aime --impl claude_opus; esoi run model_quality_aime --impl gemini_2_5_flash_lite; esoi run model_quality_aime --impl gemini_2_5_flash; esoi run model_quality_aime --impl gpt_5_nano; esoi run model_quality_aime --impl gpt_5_mini; esoi run model_quality_aime --impl deepseek_flash`
- Vendor arms answer (`metric-vendor-answers`): `esoi run call_a_model --impl gemini; esoi run call_a_model --impl openai; esoi run call_a_model --impl deepseek; esoi run call_a_model --impl claude_cli`
- Provider failover (`metric-vendor-model-caller`): `esoi run provider_failover --impl multi_provider`
- Model asked at the tier, within the budget (`metric-model-plumbing`): `esoi run model_call --impl via_vendor`
- Days since each seat was researched (`metric-the-learning`): `none`
- Registry freshness reading (`metric-research-freshness-reader`): `esoi run stay_current --impl registry_scan`
- Public stage sourced and triangulated (`metric-public-stage-sourced-and-triangulated`): `none`
- Best in circumstance with variants (`metric-best-in-circumstance-with-variants`): `none`
- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`): `python3 -m pytest tests/test_deep_session_subagents.py`
- Research question finds its paper (`metric-the-science`): `esoi run know_the_world --impl openalex_semantic_and_web; esoi run know_the_world --impl openalex_semantic; esoi run know_the_world --impl web_research; esoi run know_the_world --impl openalex; esoi run know_the_world --impl openalex_keywords; esoi run know_the_world --impl openalex_keywords_model`
- Search finds the source (`metric-web-search`): `esoi run search_backend --impl gemini; esoi run search_backend --impl provider; esoi run search_backend --impl searxng; esoi run search_backend --impl brave; esoi run search_backend --impl serper; esoi run search_backend --impl tavily`
- The best integration of each category is chosen (`metric-the-tools`): `none`
- Goal met by its own tests (`metric-file-editing`): `esoi run file_edit_goals --impl fast_edit; esoi run file_edit_goals --impl none`
- Goal met by its own tests (agent sessions) (`metric-delegated-agent-sessions`): `esoi run file_edit_goals --impl subprocess_goal_runner; esoi run file_edit_goals --impl stream_json_goal_runner; esoi run file_edit_goals --impl acp_deep_runner; esoi run file_edit_goals --impl none`
- Share of connections that need no code (`metric-connection-config-share`): `python3 -m pytest tests/test_registry.py tests/test_areas.py`
- The operation is carried out and nothing else (`metric-connected-system-operations`): `none`
- Files read inside the folder (`metric-read-files`): `python3 -m pytest tests/test_act_read_files.py`
