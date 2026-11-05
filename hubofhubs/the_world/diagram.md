These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Awareness of the outside and interaction with it

World is how the system learns what is outside it and acts on it. Science returns observations of public research that a reader can cite. Tools lets the AI use the tool of a category through Web Search, File Reading, File Editing, Connected System Operations or Delegated Agent Sessions, and refuses a category the authority does not allow. File Editing makes its one-call edit through Vendor Model Caller at the tier that Model Tier Chooser picks. Model Plumbing is how every part asks a model, through Model Tier Chooser and Vendor Model Caller. Vendor Model Caller steps to the next provider when one fails. Learning keeps the research current by reading dates through Research Freshness Reader.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Vendor Model Caller<br/><i>vendor-model-caller</i>"]
    s1["Model Tier Chooser<br/><i>model-tier-chooser</i>"]
    s2["Model Plumbing<br/><i>model-plumbing</i>"]
    s3["Learning<br/><i>the-learning</i>"]
    s4["Research Freshness Reader<br/><i>research-freshness-reader</i>"]
    s5["Science<br/><i>the-science</i>"]
    s6["Web Search<br/><i>web-search</i>"]
    s7["Tools<br/><i>the-tools</i>"]
    s8["File Editing<br/><i>file-editing</i>"]
    s9["Connected System Operations<br/><i>connected-system-operations</i>"]
    s10["Delegated Agent Sessions<br/><i>delegated-agent-sessions</i>"]
    s11["File Reading<br/><i>read-files</i>"]
    s0 -->|"Text, a plan or a list of models"| s2
    s0 -->|"Text, a plan or a list of models"| s8
    s1 -->|"A mapping from each tier to the chosen provider and model"| s2
    s1 -->|"A mapping from each tier to the chosen provider and model"| s8
    s2 -->|"The model's answer to a prompt at a tier"| s5
    s4 -->|"Days since the date, or the combined freshness reading with the stale areas named"| s3
    s6 -->|"A response of hits (title, link, snippet, date, passages and their kind), an optional direct answer and the queries issued; raises SearchBackendError on failure"| s5
    s6 -->|"A response of hits (title, link, snippet, date, passages and their kind), an optional direct answer and the queries issued; raises SearchBackendError on failure"| s7
    s8 -->|"A report of the file change, or the reason it was declined; nothing changes when it declines"| s7
    s9 -->|"The result of the operation, or the reason it was declined"| s7
    s10 -->|"A result that says whether the goal was met, with the reason"| s7
    s11 -->|"The file paths of a folder, and the text of the files asked for"| s7
```
