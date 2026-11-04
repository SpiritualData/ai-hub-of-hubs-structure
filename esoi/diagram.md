These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: The best parts for AI intelligence, assembled and proven

hub-of-hubs gives anyone a working AI assembled from measured open-source parts, and assemble-the-whole is the one call that holds it together. It answers a question through take-in-the-world and remember-and-recall, holds that answer to its sources through think-critically, asks a model at a measured tier through reason-and-answer, carries a goal out through act-in-the-world only after watch-for-risk lets the step pass, and checks that the hub stays generic through keep-it-generic. take-in-the-world brings outside material in by running a web search through search-backend and, for research questions, a paper lookup through know-the-world. remember-and-recall keeps cards in card-store, draws the cards a query needs by relevance through context-assembler, and fills the store from a folder's files through cards-from-files. cards-from-files groups a folder's files into topic cards by which files import each other, so it writes them without asking a model. reason-and-answer sends a question to the model that choose-a-model-tier measured best for the tier, through model-call, which is built on call-a-model. act-in-the-world makes each file edit with a single request through call-a-model, at the tier that choose-a-model-tier picks. keep-it-generic audits the hub for consumer wording and learns how stale its research is through stay-current. keep-it-generic also learns how much of the hub connects by configuration through connect-any-integration. stay-current lists the areas whose research is older than ninety days by reading their dates through read-registry-freshness. connect-any-integration reports the share of connections that need no code by scoring them through score-hub-connections.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["take-in-the-world: the World seat<br/>take-in-the-world"]
    s1["reason-and-answer: the Mind seat<br/>reason-and-answer"]
    s2["choose-a-model-tier: pick the model for...<br/>choose-a-model-tier"]
    s3["know-the-world: the Science seat<br/>know-the-world"]
    s4["act-in-the-world: the Body seat<br/>act-in-the-world"]
    s5["watch-for-risk: the Overseer seat<br/>watch-for-risk"]
    s6["assemble-the-whole: the The whole being...<br/>assemble-the-whole"]
    s7["stay-current: the Learning seat<br/>stay-current"]
    s8["read-registry-freshness: how old is...<br/>read-registry-freshness"]
    s9["keep-it-generic: the Character seat<br/>keep-it-generic"]
    s10["connect-any-integration: the Hands seat<br/>connect-any-integration"]
    s11["score-hub-connections: how much of an...<br/>score-hub-connections"]
    s12["card-store: a place to keep and find...<br/>card-store"]
    s13["think-critically: the Critical thinking...<br/>think-critically"]
    s14["model-call: ask a model one question<br/>model-call"]
    s15["call-a-model: ask a vendor's model to...<br/>call-a-model"]
    s16["remember-and-recall: the Subconscious...<br/>remember-and-recall"]
    s17["context-assembler: pick the context a...<br/>context-assembler"]
    s18["cards-from-files: cards for a folder<br/>cards-from-files"]
    s19["search-backend: run one web search<br/>search-backend"]
    s0 -->|"Outside material for a task, from the search backends"| s6
    s1 -->|"The text a model answers to the prompt at that tier"| s6
    s2 -->|"A mapping from each tier to the chosen provider and model"| s1
    s2 -->|"A mapping from each tier to the chosen provider and model"| s4
    s3 -->|"One observation: title, link and snippet per hit, or the..."| s0
    s4 -->|"A DeepResult that says whether the goal was met, with the..."| s6
    s5 -->|"One signal: proceed, redirect, answer_now, escalate_deep or..."| s6
    s7 -->|"The names of the registry's areas whose research is older..."| s9
    s8 -->|"Days since the date, or the combined freshness reading with..."| s7
    s9 -->|"Seats whose wording is data, whose arms are current and..."| s6
    s10 -->|"The share, from 0 to 1, of the area's hub connections that..."| s9
    s11 -->|"Per-area checks and a combined score"| s10
    s12 -->|"The id of an added card, a card or nothing for an id, the..."| s16
    s13 -->|"The findings, one per claim the evidence does not support..."| s6
    s14 -->|"The text a model answers to the prompt"| s1
    s14 -->|"The text a model answers to the prompt"| s3
    s15 -->|"Text, a plan or a list of models"| s4
    s15 -->|"Text, a plan or a list of models"| s5
    s15 -->|"Text, a plan or a list of models"| s14
    s15 -->|"Text, a plan or a list of models"| s18
    s16 -->|"The cards a task needs, in one rendered view with their ids"| s6
    s17 -->|"An assembled context view and the ids of the cards it drew..."| s16
    s18 -->|"Cards in the card-store record shape (grouping, summary..."| s16
    s19 -->|"A response of hits (title, link, snippet, date, passages..."| s0
    s19 -->|"A response of hits (title, link, snippet, date, passages..."| s3
```
