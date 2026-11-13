These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Finding and preparing information for the Mind

This part finds and prepares information before it is asked for. Local File Context makes the files of a working folder usable as context. It builds the cards of the folder through Cards From Files. It chooses which files of the folder a piece of work sees first and which folders are left out through Folder View. Context Retriever picks the cards and file units that bear on the request. Focus Context gathers the notes a person saved about their own named focus, ranks that focus first through the Context Retriever and writes the brief and the one line a session starts with. Intuition offers what occurs to the system unasked. Relevant Solutions names the consumer's ESOI solutions a request concerns, with the scopes above each and the solutions relying on each.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Context Retriever<br/><i>context-retriever</i>"]
    s1["Focus Context<br/><i>focus-context</i>"]
    s2["Local File Context<br/><i>local-file-context</i>"]
    s3["Cards From Files<br/><i>cards-from-files</i>"]
    s4["Folder View<br/><i>folder-view</i>"]
    s0 -->|"Hits: unit id, file, first line, score, tokens and text, best first; an empty list means no context is needed"| s1
    s3 -->|"Cards in the card-store record shape (grouping, summary, keywords, files with their hashes), and the ids of kept cards whose files changed"| s2
    s4 -->|"Picks best first (relative path, reason, size; named when the goal names it; flagged when it names a file inside a risky folder), the folders and risky files left out with the reason of each, and counts of the files passed over one by one"| s2
```
