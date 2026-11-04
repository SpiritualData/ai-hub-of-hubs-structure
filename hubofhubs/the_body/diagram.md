These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: The form and internal context of a system

Body is the form of the system and the context that belongs to it, and it lets anyone apply the hub to their own system by providing adapters or declaring their APIs and databases. Internal Context keeps what the system knows in Card Store and proposes the cards a folder of files needs through Cards From Files. Learning names the areas whose research is older than ninety days by reading their dates through Research Freshness Reader. Nervous System raises one small signal before a step that cannot be undone or belongs to a person. Hands lets the AI use outside services, change things outside and bring knowledge in without being one specific integration, and it reports how much of that is catalog data through Connection Scorer. Acting takes a goal with a written done-standard and tries to bring it about, and it reports whether the goal was met.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Cards From Files<br/><i>cards-from-files</i>"]
    s1["Learning<br/><i>stay-current</i>"]
    s2["Research Freshness Reader<br/><i>read-registry-freshness</i>"]
    s3["Hands<br/><i>connect-any-integration</i>"]
    s4["Connection Scorer<br/><i>score-hub-connections</i>"]
    s5["Card Store<br/><i>card-store</i>"]
    s6["Internal Context<br/><i>internal-context</i>"]
    s0 -->|"Cards in the card-store record shape (grouping, summary..."| s6
    s2 -->|"Days since the date, or the combined freshness reading with..."| s1
    s4 -->|"Per-area checks and a combined score"| s3
    s5 -->|"The id of an added card, a card or nothing for an id, the..."| s6
```
