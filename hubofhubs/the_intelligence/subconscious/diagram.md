These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Finding and preparing information for the Mind

This part finds and prepares information before it is asked for. Local File Context makes the files of a working folder usable as context. It builds the cards of the folder through Cards From Files. It chooses which files of the folder a piece of work sees first and which folders are left out through Folder View. Context Retriever picks the cards and file units that bear on the request. Intuition offers what occurs to the system unasked. Relevant Solutions names the consumer's ESOI solutions a request concerns, with the scopes above each and the solutions relying on each.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Local File Context<br/><i>local-file-context</i>"]
    s1["Cards From Files<br/><i>cards-from-files</i>"]
    s2["Folder View<br/><i>folder-view</i>"]
    s1 -->|"Cards in the card-store record shape (grouping, summary, keywords, files with their hashes), and the ids of kept cards whose files changed"| s0
    s2 -->|"Picks best first (relative path, reason, size; named when the goal names it; flagged when it names a file inside a risky folder), the folders and risky files left out with the reason of each, and counts of the files passed over one by one"| s0
```
