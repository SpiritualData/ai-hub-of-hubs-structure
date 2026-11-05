These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: The parts working as one whole

The Self keeps the parts of the system working as one whole, and Role Understanding states what each part is for so that no part does another's work. The Assembler builds the whole from configuration in one call and answers a request with the arms the hub selected, and it asks Integrity whether the hub still stays generic, with claims that match evidence and records that match code.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Assembler<br/><i>assemble-the-whole</i>"]
    s1["Integrity<br/><i>keep-it-generic</i>"]
    s1 -->|"Consumer-specific strings found, stale areas and the share..."| s0
```
