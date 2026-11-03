# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Layer | Role | Serves |
|---|---|---|---|
| `esoi-records` | docs | The intent, problems, ideals, solutions, implementations and metrics records, their generated docs and the checker configuration | assemble-the-whole |
| `status-script` | scripts | Rewrites the status block of README.md from the records, and its test | read-registry-freshness |
| `hub-registry` | docs | The registry of hubs (areas, researched candidates, each consumer hub connections and hand-wired services), the example lane config and the guides | read-registry-freshness, score-hub-connections |
| `hub-scorer` | core | The scorer that reads the registry with a consumer binding: eight checks per area and a combined score | read-registry-freshness, score-hub-connections, choose-a-model-tier, watch-for-risk, card-store |
| `hub-ports` | core | : neutral ports moved out of a consumer core (usage scope, model provider, context assembly) | remember-and-recall, reason-and-answer |
| `hub-websearch` | core | : the search-backend arms and the web research code moved out of a consumer (backends, cache, limiter, page fetch and extraction, the research adapter) | search-backend |
| `hub-models` | core | Model vendor arms, the router and the Claude program arm. | call-a-model, model-call, reason-and-answer |
| `hub-recall` | core | The card store, context assemblers and card builders. | remember-and-recall, context-assembler, cards-from-files |
| `hub-critique` | core | Link detection and the evidence check that holds an answer to its sources. | think-critically |
| `hub-act` | core | The file-editing arm, the folder writer and operation writing over MCP. | act-in-the-world |
| `hub-science` | core | Scholarly search arms over OpenAlex. | know-the-world |
| `hub-deep` | core | Agent runners that drive Claude Code or an ACP agent. | act-in-the-world |
| `hub-orchestrate` | core | The planning and answering loop moved from a consumer. | reason-and-answer |
| `hub-evaluation` | evaluation | The per-seat cases, scorers and arm wrappers that esoi runs to record results. | assemble-the-whole |
| `hub-terminal` | core | : pure renderers from run events to framework-free blocks for any terminal frontend (work trace, interim folding, asks, stopped reason),  moved in from a consumer | take-in-the-world |
