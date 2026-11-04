These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Processing information for one request

Intelligence turns what is known into one answer for one request. Mind is what the planning and responding AI can see for that request and how it outputs plans, requests and communications, and it asks a model through Model Tier Chooser and Model Call. Subconscious finds and prepares information for the answering AI, drawing the cards a request needs through Context Assembler. Intuition offers what surfaces for a request unasked. Context Retriever picks the pieces of a folder's files that a task needs within a token budget. Higher Mind keeps the long view through Long-Term Memory, Long-Term Context and Objectives. Critical Thinking holds an answer to the evidence behind it.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Subconscious<br/><i>remember-and-recall</i>"]
    s1["Context Assembler<br/><i>context-assembler</i>"]
    s2["Context Retriever<br/><i>retrieve-context</i>"]
    s3["Higher Mind<br/><i>higher-mind</i>"]
    s4["Long-Term Memory<br/><i>long-term-memory</i>"]
    s5["Long-Term Context<br/><i>long-term-context</i>"]
    s6["Objectives<br/><i>hold-objectives</i>"]
    s1 -->|"An assembled context view and the ids of the cards it drew..."| s0
    s2 -->|"Hits: unit id, file, first line, score, tokens and text..."| s1
    s4 -->|"Remembered events that bear on a request"| s3
    s5 -->|"Standing facts that bear on a request"| s3
    s6 -->|"The objectives in progress and their state"| s3
```
