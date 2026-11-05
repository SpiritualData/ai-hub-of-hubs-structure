# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Handle | Layer | Role | Serves |
|---|---|---|---|---|
| Records and top intent | `esoi-records` | docs | The intent, problems, ideals, solutions, implementations and metrics records, their generated docs and the checker configuration | the-assembler |
| Status script | `status-script` | scripts | Rewrites the status block of README.md from the records, and its test | research-freshness-reader |
| Registry and docs | `hub-registry` | docs | The registry of hubs (areas, researched candidates, each consumer hub connections and hand-wired services), the example lane config and the guides | research-freshness-reader, the-tools, the-hands |
| Scorer and assembly core | `hub-scorer` | core | The scorer that reads the registry with a consumer binding: eight checks per area and a combined score | research-freshness-reader, the-tools, the-hands, model-tier-chooser, nervous-system, card-store, the-self, the-body, the-intelligence, the-consciousness, internal-context, higher-mind, the-mind, model-plumbing |
| Ports | `hub-ports` | core | : neutral ports moved out of a consumer core (usage scope, model provider, context assembly) | the-subconscious, the-mind |
| Web search code | `hub-websearch` | core | : the web-search arms and the web research code moved out of a consumer (backends, cache, limiter, page fetch and extraction, the research adapter) | web-search |
| Model vendor code | `hub-models` | core | Model vendor arms, the router and the Claude program arm. | vendor-model-caller, the-mind |
| Recall and card code | `hub-recall` | core | The card store, context assemblers and card builders. | the-subconscious, cards-from-files |
| Retrieval code | `hub-retrieval` | core | Retrieval of the context a task needs from a corpus of files under a token budget: chunking and descriptors, lexical, latent and dense arms, fusion, reranking, priors, a learned reranker and abstention. | context-retriever |
| Critique code | `hub-critique` | core | Link detection and the evidence check that holds an answer to its sources. | critical-thinking, response-quality, goal-completion |
| Action code | `hub-act` | core | The file-editing arm, the folder writer and operation writing over MCP. | file-editing, connected-system-operations, delegated-agent-sessions, read-files |
| Science code | `hub-science` | core | Scholarly search arms over OpenAlex. | the-science |
| Agent runner code | `hub-deep` | core | Agent runners that drive Claude Code or an ACP agent. | file-editing, connected-system-operations, delegated-agent-sessions |
| Orchestration code | `hub-orchestrate` | core | The planning and answering loop moved from a consumer. | the-mind, context-intake, request-planner, work-delegation, response-writer, metric-translation |
| Evaluation code | `hub-evaluation` | evaluation | The per-seat cases, scorers and arm wrappers that esoi runs to record results. | the-assembler |
| Terminal renderers | `hub-terminal` | core | : pure renderers from run events to framework-free blocks for any terminal frontend (work trace, interim folding, asks, stopped reason),  moved in from a consumer | the-world |
| Consciousness code | `hub-consciousness` | core | Representatives, Judgment Calls and Request Intake: the person's authority, the decision to ask and the requests taken in. | the-representatives, judgment-calls, request-intake |
| Intake adapters | `hub-intake` | core | The adapters that say where a system's requests come from. | intake-sources |
| Proactivity code | `hub-proactivity` | core | Which standing schedules are due, by calendar period, requested run or event. | the-proactivity |
