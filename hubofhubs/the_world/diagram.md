These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Awareness of the outside and interaction with it

World is how the system learns what is outside it and acts on it. Science returns observations of public research that a reader can cite. Tools lets the AI use the tool of a category through Web Search, File Reading, File Editing, Connected System Operations or Delegated Agent Sessions, and refuses a category the authority does not allow. File Editing makes its one-call edit through Vendor Model Caller at the tier that Model Tier Chooser picks. Model Plumbing is how every part asks a model, through Model Tier Chooser and Vendor Model Caller. Vendor Model Caller steps to the next provider when one fails. Learning keeps the research current by reading dates through Research Freshness Reader.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Model Plumbing<br/><i>model-plumbing</i>"]
    s1["Science<br/><i>the-science</i>"]
    s2["Learning<br/><i>the-learning</i>"]
    s3["Research Freshness Reader<br/><i>research-freshness-reader</i>"]
    s0 -->|"The model's answer to a prompt at a tier"| s1
    s3 -->|"Days since the date, or the combined freshness reading with the stale areas named"| s2
```
