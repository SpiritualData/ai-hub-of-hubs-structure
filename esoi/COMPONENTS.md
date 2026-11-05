# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Handle | Layer | Role | Serves |
|---|---|---|---|---|
| esoi-records | `esoi-records` | docs | The intent, problems, ideals, solutions, implementations and metrics records, their generated docs and the checker configuration | assemble-the-whole |
| status-script | `status-script` | scripts | Rewrites the status block of README.md from the records, and its test | read-registry-freshness |
| hub-registry | `hub-registry` | docs | The registry of hubs (areas, researched candidates, each consumer hub connections and hand-wired services), the example lane config and the guides | read-registry-freshness, use-tools, connect-any-integration |
| hub-scorer | `hub-scorer` | core | The scorer that reads the registry with a consumer binding: eight checks per area and a combined score | read-registry-freshness, use-tools, connect-any-integration, choose-a-model-tier, watch-for-risk, card-store, the-self, the-body, the-intelligence, the-consciousness, internal-context, higher-mind, reason-and-answer, model-plumbing |
| hub-ports | `hub-ports` | core | : neutral ports moved out of a consumer core (usage scope, model provider, context assembly) | remember-and-recall, reason-and-answer |
| hub-websearch | `hub-websearch` | core | : the search-backend arms and the web research code moved out of a consumer (backends, cache, limiter, page fetch and extraction, the research adapter) | search-backend |
| hub-models | `hub-models` | core | Model vendor arms, the router and the Claude program arm. | call-a-model, model-call, reason-and-answer |
| hub-recall | `hub-recall` | core | The card store, context assemblers and card builders. | remember-and-recall, context-assembler, cards-from-files |
| hub-retrieval | `hub-retrieval` | core | Retrieval of the context a task needs from a corpus of files under a token budget: chunking and descriptors, lexical, latent and dense arms, fusion, reranking, priors, a learned reranker and abstention. | retrieve-context |
| hub-critique | `hub-critique` | core | Link detection and the evidence check that holds an answer to its sources. | think-critically, response-quality |
| hub-act | `hub-act` | core | The file-editing arm, the folder writer and operation writing over MCP. | edit-files, connected-system-operations, delegated-agent-sessions |
| hub-science | `hub-science` | core | Scholarly search arms over OpenAlex. | know-the-world |
| hub-deep | `hub-deep` | core | Agent runners that drive Claude Code or an ACP agent. | edit-files, connected-system-operations, delegated-agent-sessions |
| hub-orchestrate | `hub-orchestrate` | core | The planning and answering loop moved from a consumer. | reason-and-answer |
| hub-evaluation | `hub-evaluation` | evaluation | The per-seat cases, scorers and arm wrappers that esoi runs to record results. | assemble-the-whole |
| hub-terminal | `hub-terminal` | core | : pure renderers from run events to framework-free blocks for any terminal frontend (work trace, interim folding, asks, stopped reason),  moved in from a consumer | take-in-the-world |
