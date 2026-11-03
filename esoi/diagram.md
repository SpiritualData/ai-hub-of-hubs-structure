These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: The best parts for AI intelligence, assembled and proven

hub-of-hubs gives anyone a working AI assembled from measured open-source parts, and assemble-the-whole is the one call that holds it together. It answers a question through take-in-the-world and remember-and-recall, holds that answer to its sources through think-critically, asks a model at a measured tier through reason-and-answer, carries a goal out through act-in-the-world only after watch-for-risk lets the step pass, and checks that the hub stays generic through keep-it-generic. take-in-the-world brings outside material in by running a web search through search-backend and, for research questions, a paper lookup through know-the-world. remember-and-recall keeps cards in card-store, draws the cards a query needs by relevance through context-assembler, and fills the store from a folder's files through cards-from-files. cards-from-files has its builder ask a model through call-a-model when it writes topic cards. reason-and-answer sends a question to the model that choose-a-model-tier measured best for the tier, through model-call, which is built on call-a-model. act-in-the-world makes each file edit with a single request through call-a-model, at the tier that choose-a-model-tier picks. keep-it-generic audits the hub for consumer wording and learns how stale its research is through stay-current. keep-it-generic also learns how much of the hub connects by configuration through connect-any-integration. stay-current lists the areas whose research is older than ninety days by reading their dates through read-registry-freshness. connect-any-integration reports the share of connections that need no code by scoring them through score-hub-connections.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["take-in-the-world: the World seat<br/>take-in-the-world"]
    s1["remember-and-recall: the Subconscious...<br/>remember-and-recall"]
    s2["reason-and-answer: the Mind seat<br/>reason-and-answer"]
    s3["choose-a-model-tier: pick the model for...<br/>choose-a-model-tier"]
    s4["know-the-world: the Science seat<br/>know-the-world"]
    s5["think-critically: the Critical thinking...<br/>think-critically"]
    s6["act-in-the-world: the Body seat<br/>act-in-the-world"]
    s7["watch-for-risk: the Overseer seat<br/>watch-for-risk"]
    s8["assemble-the-whole: the The whole being...<br/>assemble-the-whole"]
    s9["stay-current: the Learning seat<br/>stay-current"]
    s10["read-registry-freshness: how old is...<br/>read-registry-freshness"]
    s11["keep-it-generic: the Character seat<br/>keep-it-generic"]
    s12["connect-any-integration: the Hands seat<br/>connect-any-integration"]
    s13["score-hub-connections: how much of an...<br/>score-hub-connections"]
    s14["card-store: a place to keep and find...<br/>card-store"]
    s15["model-call: ask a model one question<br/>model-call"]
    s16["search-backend: run one web search<br/>search-backend"]
    s17["call-a-model: ask a vendor's model to...<br/>call-a-model"]
    s18["context-assembler: pick the context a...<br/>context-assembler"]
    s19["cards-from-files: cards for a folder<br/>cards-from-files"]
    s0 -->|"Outside material for a task, from the search backends"| s8
    s1 -->|"The cards a task needs, in one rendered view with their ids"| s8
    s2 -->|"An answer worked out through measured model calls"| s8
    s3 -->|"A mapping from each tier to the chosen provider and model"| s2
    s3 -->|"A mapping from each tier to the chosen provider and model"| s6
    s4 -->|"Observations about the world a reader can cite"| s0
    s5 -->|"The findings, one per claim the evidence does not support..."| s8
    s6 -->|"A DeepResult that says whether the goal was met, with the..."| s8
    s7 -->|"One signal: proceed, redirect, answer_now, escalate_deep or..."| s8
    s9 -->|"Each seat's candidates, researched and dated this week"| s11
    s10 -->|"Days since the date, or the combined freshness reading with..."| s9
    s11 -->|"Seats whose wording is data, whose arms are current and..."| s8
    s12 -->|"An integration as a catalog entry, with its connection..."| s11
    s13 -->|"Per-area checks and a combined score"| s12
    s14 -->|"The stored cards, and the cards matching a query or a tag"| s1
    s15 -->|"The text a model answers to one prompt at a tier"| s2
    s15 -->|"The text a model answers to one prompt at a tier"| s4
    s16 -->|"Hits for a query: title, link and snippet per hit"| s0
    s16 -->|"Hits for a query: title, link and snippet per hit"| s4
    s17 -->|"Text, a plan or a list of models"| s6
    s17 -->|"Text, a plan or a list of models"| s7
    s17 -->|"Text, a plan or a list of models"| s15
    s17 -->|"Text, a plan or a list of models"| s19
    s18 -->|"An assembled context view and the ids of the cards it drew..."| s1
    s19 -->|"Cards in the card-store record shape (grouping, summary..."| s1
```
