# The registry, area by area

Every area the hub tracks, grouped by the seat it serves. An area is one narrow job a hub can do for a part of an AI mind; a
broad seat is broken into sub-solution areas so each can be compared on its own metric. Each area carries 2 to 16 researched
candidates in `hubofhubs/registry/hub_findings.csv` (an area with a single named candidate carries 1), each with a licence, a
dated evidence URL and the quality of the source. A claim not read on a primary page is marked unverified in its row.

The file is generated: run `python3 scripts/status.py` and never edit between the markers by hand. How an area is refreshed is in
[the weekly refresh](refresh.md); how the files join is in [connect a hub](connect-a-hub.md).

<!-- registry:start -->
### hold-the-intents (Higher mind)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| intents | Keeping the intent hierarchy and choosing which representative acts | compared | coexist | none | Agent Skills specification; A2A protocol; OpenAI Agents SDK; Claude Agent SDK; semantic-router | 10 | 2026-10-30 |

### take-in-the-world (World)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| channels | Two-way chat channels | builds_on | keep | OpenClaw | none | 1 | 2026-10-30 |
| inbound_mail | Turning real people's mail into asks | compared | coexist | none | Google Gmail remote MCP; workspace-mcp; AgentMail; Postmark inbound; Nylas | 4 | 2026-10-30 |
| voice | Spoken conversation with the brain | compared | keep | none | Pipecat; LiveKit Agents; OpenAI Realtime API; faster-whisper; whisper.cpp; Deepgram; TEN Framework | 7 | 2026-10-30 |
| integration_aggregators | One connection to the long tail of apps with managed auth | compared | coexist | none | Composio; Activepieces; Pipedream Connect; Nango; Arcade; Klavis AI; n8n; Zapier MCP | 10 | 2026-10-30 |
| agent_auth | Acting as a person on an app without the model seeing the secret | compared | keep | none | Nango; Arcade; Composio managed auth; Pipedream Connect; Paragon ActionKit | 5 | 2026-10-30 |
| vendor_mcp | First-party hosted MCP servers of the apps SD already uses | compared | coexist | none | Google Workspace MCP servers; Notion hosted MCP server; makenotion notion-mcp-server | 3 | 2026-10-30 |
| inbound_events | Being told when something happens in an app instead of polling | compared | watch | none | Nango webhooks; Composio triggers; Pipedream triggers; Claude Code channels; MCP Tasks extension; Svix | 6 | 2026-10-30 |

### remember-and-recall (Subconscious, Intuition)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| vector_store | Storing and searching scoped cards and chunks | builds_on | keep | Qdrant | LanceDB; Chroma; pgvector; Weaviate; Vespa; turbopuffer; sqlite-vec; MongoDB Community Search | 9 | 2026-10-30 |
| embeddings | Turning text into vectors for the dense arm | builds_on | coexist | fastembed, Voyage embeddings | Qwen3-Embedding-0.6B; EmbeddingGemma-300m; BGE-M3; Gemini embedding | 4 | 2026-10-30 |
| context_assembly | Choosing the context a turn sees | compared | coexist | bm25s, Qdrant and fastembed, bge-small-en-v1.5 | Qdrant native weighted RRF hybrid; Qwen3-Embedding-0.6B; EmbeddingGemma-300m; contextual retrieval prefix; LanceDB; PyLate; Haystack; LlamaIndex | 15 | 2026-10-30 |
| code_context | Choosing files and symbols for a code task | compared | coexist | Agentic glob and grep inside Claude Code, QAR context cards | Aider repository map; Serena; Augment Context Engine; Cursor semantic search; tree-sitter repository map | 6 | 2026-10-30 |
| reranking | Ordering a shortlist of candidate context | compared | coexist | cheap-model batched judge (QAR spec_selection) | Qwen3-Reranker; bge-reranker-v2-m3; Qdrant multivector rescoring; Cohere Rerank; Voyage rerank | 5 | 2026-10-30 |
| memory | Remembering what a person taught over time | compared | coexist | QAR card store and conversation recall | Graphiti; Mem0; Hindsight; Cognee; Letta; Supermemory; LangMem; A-MEM | 9 | 2026-10-30 |
| background_memory | Precomputing and whispering context while idle | compared | coexist | QAR anticipation engine and context updates feed | Letta sleep-time compute; claude-subconscious; Anthropic memory tool; LangMem background manager | 3 | 2026-10-30 |
| context_compression | Keeping long runs inside the window | compared | keep | QAR prompt budget and recency window | Anthropic compaction and context editing patterns; Factory structured summarization; LLMLingua-2 | 3 | 2026-10-30 |
| graph_rag | Answering cross-document and global questions over huge corpora | compared | keep | none | LightRAG; Microsoft LazyGraphRAG; HippoRAG 2; RAPTOR | 5 | 2026-10-30 |
| science_provenance | Making a result re-derivable and shareable | compared | adopt | none | RO-Crate (rocrate); prov; MLflow; DVC; OpenLineage; nanopub; Snakemake | 7 | 2026-10-30 |

### reason-and-answer (Mind)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| agent_orchestration | Planning, gathering and answering a request in a bounded loop | compared | coexist | none | Pydantic AI; LangGraph; OpenAI Agents SDK; Google ADK; Microsoft Agent Framework; Claude Agent SDK | 14 | 2026-10-30 |
| structured_output | Getting a model's decision back as valid structured data | compared | adopt | none | Anthropic structured outputs; Instructor; Outlines; BAML | 4 | 2026-10-30 |
| prompt_optimization | Improving prompts by measured metric | compared | coexist | none | GEPA; DSPy | 2 | 2026-10-30 |
| model_providers | Calling any model vendor with tier fallback | compared | coexist | none | Bifrost; OpenRouter; Vercel AI Gateway; Portkey gateway; any-llm; LiteLLM | 9 | 2026-10-30 |
| deep_run_cost | Keeping a long agent run small and cached | compared | keep | none | Claude Code prompt caching; PreToolUse output-filter hooks; observation masking; context editing; OpenHands condenser; CliffCompaction | 7 | 2026-10-30 |
| prompt_cache | Reusing prompt prefixes to cut cost and time | compared | keep | QAR stable render order | Anthropic prompt caching; LMCache | 3 | 2026-10-30 |

### know-the-world (Science)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| web_search | Grounding answers on the live web | builds_on | adopt | SearXNG, Serper, Brave Search API, Tavily, Gemini Google Search grounding | Exa; Parallel; Perplexity Search API; Brave LLM Context; Anthropic web search server tool | 8 | 2026-10-30 |
| page_extraction | Turning a fetched page or file into clean text | builds_on | adopt | trafilatura (optional), own stdlib extractor and BM25 | Crawl4AI; Firecrawl; Jina Reader; Docling; MarkItDown | 7 | 2026-10-30 |
| deep_research | Multi-step open-web research reports | compared | coexist | none | GPT Researcher; Exa deep search and agent; STORM | 5 | 2026-10-30 |
| science_find_evidence | Finding papers and sources for a question | compared | adopt | none | OpenAlex API; cyanheads/openalex-mcp-server; Asta Scientific Corpus MCP; Semantic Scholar API; PubMed MCP server; Europe PMC REST API; Crossref REST API; Elicit API v2; Undermind; Consensus hosted MCP; SYNERGY screening datasets | 14 | 2026-10-30 |
| science_read_papers | Cited answers and extraction from full-text papers | compared | adopt | none | PaperQA2; Ai2 Scholar QA library; OpenScholar; Edison literature agent client; Docling; marker; unstructured | 7 | 2026-10-30 |
| science_verify_claims | Checking that a source supports a claim and grading evidence | compared | adopt | none | scite MCP; PaperQA2 contradiction detection; DeepSciVerify; Inspect AI | 4 | 2026-10-30 |
| science_hypotheses | Proposing and ranking candidate explanations | compared | keep | none | Google Co-Scientist; Kosmos; Robin; AI Scientist v2; Agent Laboratory; AI-Researcher; BioVerge | 7 | 2026-10-30 |
| science_statistics | Pooling evidence and quantifying uncertainty | compared | coexist | none | PyMC; bambi; ArviZ; statsmodels; SciPy; PyMARE; DoWhy; EconML; pingouin | 9 | 2026-10-30 |
| science_graph | Representing papers, constructs and theories as a graph | compared | adopt | none | SemOpenAlex; ORKG; Microsoft GraphRAG; LightRAG; Graphiti; Cognee; rdflib and pySHACL | 7 | 2026-10-30 |
| science_estimate_truth | Estimating how likely a hypothesis is to hold | compared | keep | none | BrainBench; Co-Scientist tournament pattern; automated multi-model review of AI scientists | 3 | 2026-10-30 |

### think-critically (Critical thinking)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| answer_verification | Checking an answer against the evidence it was built from | compared | coexist | none: no groundedness detector today, claim-vs-execution judge in core/orchestrator_judges.py and the structural sufficiency gate in hubofhubs/critique/sufficiency.py are the nearest | Vectara HHEM-2.1-Open; MiniCheck; Granite Guardian 4.1; Anthropic Citations; Amazon Bedrock contextual grounding; NeMo Guardrails fact-check rails | 9 | 2026-10-30 |
| link_checking | No reply carries a link nobody checked | builds_on | keep | hubofhubs/critique/link_guard.py (803 lines) and link_detect.py | lychee | 1 | 2026-10-30 |
| judging | Model-graded judging of answers and decisions | compared | coexist | QAR runtime judges (core/orchestrator_judges.py, quest_judge.py, reach_judge.py) and evaluation/components/claude_judge.py | DeepEval; Inspect AI; TruLens; promptfoo; Patronus Glider | 5 | 2026-10-30 |
| metric_enforcement | Holding every request to its ESOI metric and recording the reading | compared | keep | core/goal_metrics.py, metric_meter.py, metric_results.py (784 lines) with a ledger | Langfuse; Arize Phoenix; Opik | 3 | 2026-10-30 |

### act-in-the-world (Body)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| durable_jobs | Running queued work once, surviving restarts | compared | keep | none | DBOS Transact; Temporal; Hatchet; Inngest; Restate | 8 | 2026-10-30 |
| browser_use | Operating web pages and screens | compared | adopt | none | Playwright MCP; Browser Use; Stagehand; Anthropic computer use tool | 6 | 2026-10-30 |
| file_writers | Changing files safely | compared | keep | Aider edit-block layer (vendored) | Morph Fast Apply; Relace Apply 3 | 3 | 2026-10-30 |
| agent_harness | Deep work done by a coding-agent harness on a Claude subscription | builds_on | coexist | Claude Code CLI, Agent Client Protocol agents (claude-agent-acp) | Codex CLI; mini-swe-agent; Goose; OpenCode; OpenHands software-agent-sdk; Cline; Aider | 11 | 2026-10-30 |
| code_edit | Editing a file reliably and cheaply | builds_on | keep | Aider SEARCH/REPLACE matcher (vendored) | Claude Code exact str_replace; Codex apply_patch; Aider udiff; Morph Fast Apply; SWE-agent linted edit | 7 | 2026-10-30 |
| code_search | Finding the right code before and during a run | compared | keep | none | Aider repo map; Claude Code LSP plugin; Serena MCP; SWE-grep; WarpGrep; Claude Code Explore subagent | 7 | 2026-10-30 |
| command_sandbox | Running agent commands without risking the host | compared | adopt | none | Anthropic sandbox-runtime; Codex CLI sandbox; bubblewrap; Docker Sandboxes; E2B; Modal | 7 | 2026-10-30 |
| subagents | Delegating and recursing inside an agent run | compared | coexist | none | Claude Code subagents; Claude Code dynamic workflows; Recursive Language Models; LangGraph; OpenAI Agents SDK; smolagents; CrewAI; AG2 | 10 | 2026-10-30 |
| agent_verify | Checking a run's work and undoing it | compared | keep | none | Claude Code checkpointing; Anthropic long-running harness pattern; Aider commit per edit; Agentless validation | 6 | 2026-10-30 |
| agent_bench | Choosing a harness by measured results | compared | keep | none | SWE-bench Verified bash-only (Vals); Terminal-Bench 2.0; Aider polyglot; SWE-bench Pro; Holistic Agent Leaderboard | 6 | 2026-10-30 |
| science_run_analysis | Designing and running analyses on data with code | compared | adopt | none | K-Dense Scientific Agent Skills; ToolUniverse; Biomni; Edison Analysis; AstaBench and Asta agents; ScienceAgentBench; Jupyter AI; E2B code interpreter | 9 | 2026-10-30 |
| mcp_gateway | Central auth, routing and audit when several consumers share MCP servers | compared | watch | none | agentgateway; IBM ContextForge; LiteLLM MCP Gateway; Docker MCP Gateway; MetaMCP; Obot; Microsoft mcp-gateway; mozilla-ai mcpd | 8 | 2026-10-30 |
| mcp_registry | Finding and vetting MCP servers | builds_on | adopt | Official MCP Registry | Smithery; PulseMCP; Glama; Docker MCP Catalog | 5 | 2026-10-30 |
| mcp_client | Speaking MCP to a server from QAR | builds_on | keep | Model Context Protocol Python SDK | FastMCP; Pydantic AI; Claude Code native MCP client | 4 | 2026-10-30 |
| openapi_tools | Turning a REST API into callable tools without writing a wrapper | compared | keep | none | FastMCP from_openapi; LiteLLM OpenAPI to MCP; agentgateway; ContextForge REST wrapping; Speakeasy; Stainless; openapi-mcp-generator | 5 | 2026-10-30 |
| tool_schema | Making a model's tool calls valid and measuring tool-calling quality | compared | adopt | none | Anthropic strict tool use; Instructor; BAML; Pydantic AI; BFCL V4; MCP-Atlas | 7 | 2026-10-30 |
| tool_discovery | Showing a model only the tools it needs | compared | keep | none | Anthropic tool search tool; Code execution with MCP; Claude Code ToolSearch; Klavis Strata; Smithery Toolbox; Programmatic tool calling | 6 | 2026-10-30 |
| tool_sandbox | Running commands and stdio MCP servers with limited reach | compared | adopt | none | Anthropic sandbox-runtime; microsandbox; E2B; Cloudflare Sandbox SDK; Modal sandboxes; Daytona | 6 | 2026-10-30 |
| tool_permissions | Deciding whether a tool call may run and who must approve it | compared | keep | none | MCP specification security principles; agentgateway CEL policies; LiteLLM MCP access groups; Cedar; Open Policy Agent; Claude Code managed MCP | 7 | 2026-10-30 |
| tool_observability | Recording what every tool call did | compared | adopt | none | OpenTelemetry GenAI semantic conventions; Langfuse; Arize Phoenix; Pydantic Logfire; ContextForge tracing | 5 | 2026-10-30 |

### watch-for-risk (Overseer)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| injection_defense | Untrusted text and tool output must not steer the agent or leak data | compared | coexist | untrusted-content framing in adapters/remote_files_adapter.py and planner prompt rules (core/planner_context.py), no classifier, no data-flow control | ProtectAI deberta-v3-base-prompt-injection-v2; Llama Prompt Guard 2; PIGuard; LlamaFirewall; Azure Prompt Shields; Google Model Armor; OpenAI Guardrails; Microsoft Agent Framework FIDES; CaMeL | 16 | 2026-10-30 |
| guardrails | Policy rails around inputs, outputs and actions | compared | keep | reply guards (hubofhubs/critique, evaluation/components/reply_guards) are product checks, not safety rails | NeMo Guardrails; Guardrails AI; gpt-oss-safeguard; Llama Guard 4; Qwen3Guard | 4 | 2026-10-30 |
| consent_gating | Stopping irreversible or human-only steps and asking the right person | builds_on | keep | core/orchestrator_decisions.py and orchestrator_decide_tool.py (1,288 lines), adapters/acp_deep_runner_session.py answers ACP session/request_permission | MCP elicitation and input_required (spec 2026-07-28); Claude Agent SDK canUseTool and hooks; LangGraph interrupt | 4 | 2026-10-30 |
| run_supervision | Watching a run and sending at most one small signal | compared | keep | hubofhubs/risk.py (297 lines) engine plus core/overseer.py and orchestrator_oversee.py (425 lines), five signals | Claude Code auto mode classifier; LlamaFirewall AlignmentCheck; Patronus Percival | 3 | 2026-10-30 |
| secrets_hygiene | Keeping secrets and real identifiers out of public code | compared | coexist | esoi.hygiene scanner in the esoi library, 35-case keep_secrets_out set | Gitleaks | 1 | 2026-10-30 |

### assemble-the-whole (The whole being)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| assembly_runtime | Resuming a run after a crash or restart | compared | watch | none | DBOS Transact | 1 | 2026-10-30 |
| assembly_observability | Seeing what each step of a turn did and cost | compared | adopt | none | OpenTelemetry GenAI semantic conventions; Langfuse | 2 | 2026-10-30 |
| assembly_protocols | Standard edges of the whole: tools, agents, UI events, model API shape | compared | watch | Model Context Protocol servers (already wired) | AG-UI; Agent2Agent (A2A) protocol; Open Responses | 3 | 2026-10-30 |

### stay-current (Learning)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| evals | Measuring and selecting between implementations | compared | coexist | esoi (evolvable-structure Python tools) | Inspect AI; promptfoo; DeepEval; DSPy and GEPA | 6 | 2026-10-30 |
| model_pricing | Knowing current model prices, limits and capabilities | compared | adopt | tier_prices.csv (hand-kept, sourced) | models.dev; LiteLLM price list; Artificial Analysis API | 5 | 2026-10-30 |
| context_benchmarks | Public case sets for judging context arms | compared | keep | none | LongMemEval; DolphinBench; MemoryBench; CORE-Bench; ContextBench; GraphRAG-Bench | 6 | 2026-10-30 |

### keep-it-generic (Character)

| Area | Serves | Status | Call | Built on | Candidates | Findings | Researched |
|---|---|---|---|---|---|---|---|
| prompts | Prompts as versioned, editable data with no consumer wording | compared | coexist | PromptSpec registry | Langfuse; MLflow Prompt Registry; Braintrust; BAML | 7 | 2026-10-30 |
| observability | Seeing what a run did, what it cost and why | compared | adopt | none | OpenTelemetry GenAI conventions; Langfuse; Arize Phoenix | 3 | 2026-10-30 |
| config | Typed, validated configuration per deployment | compared | coexist | QAR config modules | pydantic-settings; Hydra | 2 | 2026-10-30 |
<!-- registry:end -->
