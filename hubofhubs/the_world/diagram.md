These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Awareness of the outside and interaction with it

World is how the system learns what is outside it and acts on it. Science returns observations of public research that a reader can cite. Tools lets the AI use the tool of a category through Web Search, File Editing, Connected System Operations, Delegated Agent Sessions or Personal Data Locations. File Editing makes its one-call edit through Vendor Model Caller at the tier that Model Tier Chooser picks. Model Plumbing is how every part asks a model, and it picks the model for each tier through Model Tier Chooser and asks that model through Model Call. Model Call reaches each vendor through Vendor Model Caller, which steps to the next provider when one fails. Learning keeps the research current by reading dates through Research Freshness Reader.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Model Call<br/><i>model-call</i>"]
    s1["Vendor Model Caller<br/><i>call-a-model</i>"]
    s2["Model Tier Chooser<br/><i>choose-a-model-tier</i>"]
    s3["Model Plumbing<br/><i>model-plumbing</i>"]
    s4["Learning<br/><i>stay-current</i>"]
    s5["Research Freshness Reader<br/><i>read-registry-freshness</i>"]
    s6["Science<br/><i>know-the-world</i>"]
    s7["Web Search<br/><i>search-backend</i>"]
    s8["Tools<br/><i>use-tools</i>"]
    s9["Personal Data Locations<br/><i>personal-data-locations</i>"]
    s10["File Editing<br/><i>edit-files</i>"]
    s11["Connected System Operations<br/><i>connected-system-operations</i>"]
    s12["Delegated Agent Sessions<br/><i>delegated-agent-sessions</i>"]
    s0 -->|"The text a model answers to the prompt"| s3
    s0 -->|"The text a model answers to the prompt"| s6
    s1 -->|"Text, a plan or a list of models"| s0
    s1 -->|"Text, a plan or a list of models"| s10
    s2 -->|"A mapping from each tier to the chosen provider and model"| s3
    s2 -->|"A mapping from each tier to the chosen provider and model"| s10
    s5 -->|"Days since the date, or the combined freshness reading with..."| s4
    s7 -->|"A response of hits (title, link, snippet, date, passages..."| s6
    s7 -->|"A response of hits (title, link, snippet, date, passages..."| s8
    s9 -->|"The locations of a person's data"| s8
    s10 -->|"A report of the file change, or the reason it was declined..."| s8
    s11 -->|"The result of the operation, or the reason it was declined"| s8
    s12 -->|"A result that says whether the goal was met, with the..."| s8
```
