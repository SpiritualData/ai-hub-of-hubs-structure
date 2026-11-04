These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: The best parts for AI intelligence, assembled and proven

hub-of-hubs gives anyone a working AI assembled from measured open-source parts, and The whole being is the one call that holds the mind together. A request enters through World in, which brings outside material in by running a web search and, for research questions, a paper lookup through Science. Subconscious, Intuition keeps what is known as cards in the card store, draws the cards a query needs by relevance through the context assembler, and fills the store from a folder's files through cards from files, which groups the files by which import each other and so writes cards without asking a model. The context retriever shows a task the pieces of a folder's files it needs, within a token budget or not at all, and feeds the context assembler. The Mind answers by sending the question to the model that the model tier chooser measured best for the tier, through the model call, which is built on the vendor model caller. Critical thinking then holds that answer to its sources, and the Overseer lets a step pass only when it is safe to take. The Body carries a goal out outside the model, making each file edit with a single request through the vendor model caller at the tier the chooser picks. Character checks that the hub stays generic: it audits for consumer wording, learns how stale the research is through Learning, which reads the dates through the research freshness reader, and learns how much of the hub connects by configuration through Hands, which reports the share of connections that need no code by scoring them through the connection scorer.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["World in<br/><i>take-in-the-world</i>"]
    s1["Mind<br/><i>reason-and-answer</i>"]
    s2["Model tier chooser<br/><i>choose-a-model-tier</i>"]
    s3["Science<br/><i>know-the-world</i>"]
    s4["Body<br/><i>act-in-the-world</i>"]
    s5["Overseer<br/><i>watch-for-risk</i>"]
    s6["The whole being<br/><i>assemble-the-whole</i>"]
    s7["Learning<br/><i>stay-current</i>"]
    s8["Research freshness reader<br/><i>read-registry-freshness</i>"]
    s9["Character<br/><i>keep-it-generic</i>"]
    s10["Hands<br/><i>connect-any-integration</i>"]
    s11["Connection scorer<br/><i>score-hub-connections</i>"]
    s12["Card store<br/><i>card-store</i>"]
    s13["Critical thinking<br/><i>think-critically</i>"]
    s14["Model call<br/><i>model-call</i>"]
    s15["Vendor model caller<br/><i>call-a-model</i>"]
    s16["Subconscious, Intuition<br/><i>remember-and-recall</i>"]
    s17["Context assembler<br/><i>context-assembler</i>"]
    s18["Cards from files<br/><i>cards-from-files</i>"]
    s19["Context retriever<br/><i>retrieve-context</i>"]
    s20["Web search<br/><i>search-backend</i>"]
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
    s15 -->|"Text, a plan or a list of models"| s19
    s16 -->|"The cards a task needs, in one rendered view with their ids"| s6
    s17 -->|"An assembled context view and the ids of the cards it drew..."| s16
    s18 -->|"Cards in the card-store record shape (grouping, summary..."| s16
    s19 -->|"Hits: unit id, file, first line, score, tokens and text..."| s6
    s19 -->|"Hits: unit id, file, first line, score, tokens and text..."| s17
    s20 -->|"A response of hits (title, link, snippet, date, passages..."| s0
    s20 -->|"A response of hits (title, link, snippet, date, passages..."| s3
```
