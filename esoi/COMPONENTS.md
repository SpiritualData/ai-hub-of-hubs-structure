# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Handle | Layer | Role | Serves |
|---|---|---|---|---|
| Records and top intent | `esoi-records` | docs | The intent, problems, ideals, solutions, implementations and metrics records, their generated docs and the checker configuration | the-assembler |
| Status script | `status-script` | scripts | Rewrites the status block of README.md from the records, and its test | research-freshness-reader |
| Registry and docs | `hub-registry` | docs | The registry of hubs (areas, researched candidates, each consumer hub connections and hand-wired services), the example lane config and the guides | research-freshness-reader, the-tools, the-hands |
| The Self code | `hub-the-self` | core | The Self: the assembly, the flow of a whole response, and Integrity. | role-understanding, system-integrity, the-assembler, the-self |
| Body code | `hub-the-body` | core | Body: internal context, the card store, run records and intake sources. | card-store, intake-sources, internal-context, the-body |
| Intelligence code | `hub-the-intelligence` | core | Intelligence: Mind, Higher Mind, Subconscious, Critical Thinking, Nervous System and Proactivity. | cards-from-files, context-intake, context-retriever, critical-thinking, delegation, goal-completion, guidance, higher-mind, live-objectives, long-term-memory, metric-translation, nervous-system, planner, proactivity, response-quality, response-writer, the-intelligence, the-intuition, the-mind, the-subconscious |
| World code | `hub-the-world` | core | World: Science, Tools, Model Plumbing and Learning. | connected-system-operations, delegated-agent-sessions, file-editing, model-plumbing, model-tier-chooser, read-files, research-freshness-reader, the-learning, the-science, the-tools, the-world, vendor-model-caller, web-search |
| Consciousness code | `hub-the-consciousness` | core | Consciousness: Representatives, Judgment Calls, Prioritization, Request Intake and the terminal blocks. | judgment-calls, prioritization, request-intake, the-consciousness, the-representatives |
| Package root and shared test support | `hub-package` | core | The package entry, the packaged selection and the tests that read the whole hub. | the-assembler |
| Evaluation code | `hub-evaluation` | evaluation | The per-seat cases, scorers and arm wrappers that esoi runs to record results. | the-assembler |
