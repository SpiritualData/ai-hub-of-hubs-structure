These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Processing information for one request

Intelligence turns one request into a response. Higher Mind keeps the long view through Long-Term Memory, Objectives and Guidance, which gives an infrequent longer-term nudge. Critical Thinking turns the request into a target with a budget through Metric Translation, records it through ESOI Application, and holds the result to it through Goal Completion and Response Quality. Subconscious finds and prepares information through Cards From Files, Context Retriever and Intuition. Mind takes the request in through Context Intake, breaks it into pieces through Planner, passes each piece to a worker through Delegation and writes the response through Response Writer. Mind asks for a signal before a risky piece from Nervous System, and for the decision for the person from Judgment Calls. An unmet goal sends the flow back to the planning step within the request's budget, and when the budget or the authority runs out the flow goes to Judgment Calls. Proactivity says what is due without being asked.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Nervous System<br/><i>nervous-system</i>"]
    s1["Critical Thinking<br/><i>critical-thinking</i>"]
    s2["Subconscious<br/><i>the-subconscious</i>"]
    s3["Context Retriever<br/><i>context-retriever</i>"]
    s4["Mind<br/><i>the-mind</i>"]
    s5["Higher Mind<br/><i>higher-mind</i>"]
    s6["Long-Term Memory<br/><i>long-term-memory</i>"]
    s7["Objectives<br/><i>live-objectives</i>"]
    s8["Intuition<br/><i>the-intuition</i>"]
    s9["Context Intake<br/><i>context-intake</i>"]
    s10["planner"]
    s11["delegation"]
    s12["Response Writer<br/><i>response-writer</i>"]
    s13["guidance"]
    s14["ESOI Application<br/><i>esoi-application</i>"]
    s15["Metric Translation<br/><i>metric-translation</i>"]
    s16["Goal Completion<br/><i>goal-completion</i>"]
    s17["Response Quality<br/><i>response-quality</i>"]
    s18["Cards From Files<br/><i>cards-from-files</i>"]
    s0 -->|"One signal: proceed, redirect, answer_now, escalate_deep or escalate_human; it never raises"| s4
    s3 -->|"Hits: unit id, file, first line, score, tokens and text, best first; an empty list means no context is needed"| s2
    s6 -->|"Remembered events that bear on a request"| s5
    s7 -->|"The objectives in progress, their hierarchy and their state"| s5
    s8 -->|"Items offered to the Mind for a request"| s2
    s9 -->|"One view of the information for a request"| s4
    s10 -->|"The pieces of a request, each with the sub-goal it must meet"| s4
    s11 -->|"The result of a piece, from the worker that did it"| s4
    s12 -->|"The written plan, request or communication"| s4
    s13 -->|"A nudge for the Planner, or nothing when none is due, and context-specific quality criteria"| s5
    s14 -->|"Edited specs and metrics, and a run of the improvement loop"| s1
    s15 -->|"A metric with a target value or improvement for a request or a sub-goal"| s1
    s16 -->|"Whether the goal was met, with the reason"| s1
    s17 -->|"The findings against each criterion of the profile; an empty list means the response held"| s1
    s18 -->|"Cards in the card-store record shape (grouping, summary, keywords, files with their hashes), and the ids of kept cards whose files changed"| s2
```
