These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: The parts working as one whole

The Self keeps the parts of the system working as one whole, and Role Understanding states what each part is for so that no part does another's work. The Assembler builds the whole from configuration in one call and asks Integrity whether the hub still stays generic, with claims that match evidence and records that match code. Model Plumbing is how every part asks a model, and it picks the model for each tier through Model Tier Chooser and asks that model through Model Call. Model Call reaches each vendor through Vendor Model Caller, which steps to the next provider when one fails.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Model Call<br/><i>model-call</i>"]
    s1["Vendor Model Caller<br/><i>call-a-model</i>"]
    s2["Model Tier Chooser<br/><i>choose-a-model-tier</i>"]
    s3["Assembler<br/><i>assemble-the-whole</i>"]
    s4["Integrity<br/><i>keep-it-generic</i>"]
    s5["Model Plumbing<br/><i>model-plumbing</i>"]
    s0 -->|"The text a model answers to the prompt"| s5
    s1 -->|"Text, a plan or a list of models"| s0
    s2 -->|"A mapping from each tier to the chosen provider and model"| s5
    s4 -->|"Seats whose wording is data, whose arms are current and..."| s3
```
