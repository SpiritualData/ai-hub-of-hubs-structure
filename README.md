# ai-hub-of-hubs-structure

**The best of the best hubs for AI intelligence, assembled, evaluated and refreshed weekly. Production-proven in Quest AI Runner.**

A consumer that connects one hub gains everything the hub supports, with no code per integration. This repository holds the
seats of an AI mind, the registry of hubs that can fill them, the scorer that reads the registry with a consumer's code, and the
ESOI records that define them.

## Not a list

A list of hubs says what exists. This repository is an assembled, evaluated structure:

- **Seats.** One narrow interface per part of an AI mind (memory, models, tools, risk, and so on).
- **Arms.** Open-source hubs, combinations of them, or a plain fallback. Arms compete for a seat on the same cases.
- **Assembly.** Configuration in, working system out: the winning arms are wired together.
- **Selection by metric.** A seat holds the arm that measures best. Taste never picks.
- **Weekly refresh.** Every area is researched and compared again before its research is 90 days old.

## The idea, as a mind

A request enters from the world, the subconscious admits only what bears on the goal, and the mind works on it, asking
science for evidence. Critical thinking holds the result to its metric, the overseer checks the risk, and then the body
acts. The higher mind above it chooses whose long view grounds the work.

```mermaid
flowchart TB
  HM["Higher mind<br/>hold-the-intents"]
  WI["World in<br/>take-in-the-world"]
  SUB["Subconscious, Intuition<br/>remember-and-recall"]
  MIND["Mind<br/>reason-and-answer"]
  SCI["Science<br/>know-the-world"]
  CT["Critical thinking<br/>think-critically"]
  OV["Overseer<br/>watch-for-risk"]
  ACT["Body and world out<br/>act-in-the-world"]
  WI --> SUB --> MIND --> CT --> OV --> ACT
  MIND <--> SCI
  CT -. "regression: retry" .-> MIND
  HM -. "rep and intents" .-> SUB
  HM -. "rep and intents" .-> MIND
```

This repository holds the seats, the registry, the scorer, the ESOI records and the code that wires arms into seats. Its core is the standard library plus `esoi`; each arm's third-party library is a per-library extra ([resolution design](docs/resolution-design.md)).

## What is here

| Path | What it is |
|---|---|
| `esoi/` | the ESOI records: intent, problems, ideals, seats (solutions), implementations, metrics |
| `hubofhubs/registry/` | the registry: areas and their hubs, researched candidates, each consumer's hub connections and hand-wired services |
| `hubofhubs/` | the scorer (`Binding`, `evaluate`, the vendor-branch scan, the case generator, the page renderer) and the assembly: `seats.py` (Protocols), `resolution.py` (the hub's one `esoi.assemble.Assembler` and its public names; the assembly itself is the library's), `cardstore.py` (the default card store) |
| `hubofhubs/examples/` | a lane config with one aggregator connection and no per-app entry |
| `hubofhubs/tiers.py` | per-tier model selection by passing work per cost, credits counted as cost ([how](docs/tier-selection.md)) |
| `docs/` | [quickstart](docs/quickstart.md), [connect a hub](docs/connect-a-hub.md), [search API entries](docs/search-api-entries.md), [the weekly refresh](docs/refresh.md) |
| `scripts/status.py` | rewrites the table below from the registry |
| `scripts/sync_uses.py` | checks (or writes) `uses_solution_ids` from typed constructor parameters, and the dependency graph |

## The registry

One row per area. The seat says which part of the mind the area serves. Candidates are researched with dated sources in
`hub_findings.csv`.

<!-- seats:start -->
| Area | Seat | Built on | Candidates | Researched |
|---|---|---|---|---|
| agent_harness | act-in-the-world | Claude Code CLI, Agent Client Protocol agents (claude-agent-acp) | Codex CLI; mini-swe-agent; Goose; OpenCode; OpenHands software-agent-sdk; Cline; Aider | 2026-10-30 |
| tools_mcp | act-in-the-world | Model Context Protocol Python SDK | Official MCP Registry; PulseMCP; GitHub MCP directory; Smithery; Glama; FastMCP; Claude Code native MCP client; agentgateway; IBM ContextForge; LiteLLM MCP Gateway; Docker MCP Gateway | 2026-10-30 |
| web_search | know-the-world | SearXNG, Serper, Brave Search API, Tavily, Gemini Google Search grounding | Exa; Parallel; Perplexity Search API; Brave LLM Context; Anthropic web search server tool; Firecrawl; Crawl4AI | 2026-10-30 |
| world | take-in-the-world | none | Composio; Activepieces; Pipedream Connect; Nango; Arcade; Klavis AI; n8n; Zapier MCP; Google Workspace MCP servers; Notion hosted MCP server | 2026-10-30 |
| context_assembly | remember-and-recall | bm25s, Qdrant and fastembed, bge-small-en-v1.5 | Qdrant native weighted RRF hybrid; Qwen3-Embedding-0.6B; EmbeddingGemma-300m; contextual retrieval prefix; LanceDB; PyLate; Haystack; LlamaIndex; Qwen3-Reranker; bge-reranker-v2-m3; Qdrant multivector rescoring; Cohere Rerank; Voyage rerank | 2026-10-30 |
| science | know-the-world | none | OpenAlex API; cyanheads/openalex-mcp-server; Semantic Scholar API; PaperQA2; Docling; Asta Scientific Corpus MCP; Europe PMC REST API; PubMed MCP server; scite MCP | 2026-10-30 |
| model_providers | reason-and-answer | none | Bifrost; OpenRouter; Vercel AI Gateway; Portkey gateway; any-llm; LiteLLM | 2026-10-30 |
| memory | remember-and-recall | QAR card store and conversation recall | Graphiti; Mem0; Hindsight; Cognee; Letta; Supermemory; LangMem; A-MEM | 2026-10-30 |
| evals | stay-current | esoi (evolvable-structure Python tools) | Inspect AI; promptfoo; DeepEval; DSPy and GEPA; Ragas | 2026-10-30 |
| voice | take-in-the-world | none | Pipecat; LiveKit Agents; OpenAI Realtime API; faster-whisper; whisper.cpp; Deepgram; TEN Framework | 2026-10-30 |
<!-- seats:end -->

Regenerate with `python3 scripts/status.py` (rewritten in place, never appended).

## How a consumer uses it

Import it the way the ESOI library is imported: a sibling checkout on `PYTHONPATH`, or install it.

```bash
PYTHONPATH=../ai-hub-of-hubs-structure python3 -c "import hubofhubs"      # sibling checkout
pip install -e ../ai-hub-of-hubs-structure                                     # or by path
pip install "hubofhubs @ git+https://github.com/SpiritualData/ai-hub-of-hubs-structure.git@main"
```

The consumer builds a `Binding` (its root, which of its solutions fill which area, its core folder, its ESOI records, and
one probe per area that registers a fake hub through the area's configuration entry) and calls `evaluate`. The result is
eight checks per area and a combined score. The hub never imports the consumer.

To use the parts themselves, a consumer registers any part it owns under its own name (`hubofhubs.register`), builds a
`AssemblyConfig` and calls `hubofhubs.assemble(config, provided={...})` ([quickstart](docs/quickstart.md)). The hub reads no
environment: settings are `AssemblyConfig` fields, and a name is never an import path.

## Selection and refresh

Each seat holds the arm that measures best on its metric (`esoi select`). Each area is researched again every week, oldest
first, by the consumer's autopilot using [the refresh instruction](docs/refresh.md); research older than 90 days counts as stale.

## Quest AI Runner

[Quest AI Runner](https://github.com/SpiritualData/quest-ai-runner) (QAR) is the production consumer. It keeps what is
specific to Quest: its adapters, its bindings (which of its modules fills which area), its prompts and the grounding of
answers in a person's goals. Its `hub_of_hubs` component hands those bindings to this scorer and records the result.

## Records and checks

```bash
PYTHONPATH=../evolvable-structure/implementations/python python3 -m esoi check
python3 -m pytest tests/test_registry.py tests/test_status.py tests/test_import_boundary.py
python3 scripts/sync_uses.py --check
```

## License

Apache-2.0, matching Quest AI Runner. See `LICENSE`.
