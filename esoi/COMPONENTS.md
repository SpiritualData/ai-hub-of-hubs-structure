# Components

Generated from `esoi/components.csv` by `esoi check --write-docs`.
Edit the CSV, never this file. The rules are listed by `esoi rules`.

| Component | Layer | Role | Serves |
|---|---|---|---|
| `esoi-records` | docs | The intent, problems, ideals, solutions, implementations and metrics records, their generated docs and the checker configuration | assemble-the-whole |
| `status-script` | scripts | Rewrites the status block of README.md from the records, and its test | stay-current |
| `hub-registry` | docs | The registry of hubs (areas, researched candidates, each consumer hub connections and hand-wired services), the example lane config and the guides | stay-current, connect-any-integration |
| `hub-scorer` | core | The scorer that reads the registry with a consumer binding: eight checks per area and a combined score | stay-current, connect-any-integration, reason-and-answer |
| `hub-ports` | core | unconfirmed: for Payal to confirm: neutral ports moved out of a consumer core (usage scope, model provider, context assembly) | remember-and-recall, reason-and-answer |
