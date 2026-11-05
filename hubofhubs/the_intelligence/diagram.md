These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Processing information for one request

Intelligence turns one request into a response. Higher Mind keeps the long view through Long-Term Memory, Objectives and Guidance, which gives an infrequent longer-term nudge. Critical Thinking turns the request into a target through Metric Translation, records it through ESOI Application, and holds the result to it through Goal Completion and Response Quality. Subconscious finds and prepares information through Intuition, Context Assembler and Context Retriever. Mind takes the request in through Context Intake, breaks it into pieces through Planner, passes each piece to a worker through Delegation and writes the response through Response Writer. Mind also asks for a signal before a risky piece from Nervous System, and for the decision for the person from Judgment Calls.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Nervous System<br/><i>watch-for-risk</i>"]
    s1["Critical Thinking<br/><i>think-critically</i>"]
    s2["Subconscious<br/><i>remember-and-recall</i>"]
    s3["Context Assembler<br/><i>context-assembler</i>"]
    s4["Context Retriever<br/><i>retrieve-context</i>"]
    s5["Mind<br/><i>reason-and-answer</i>"]
    s6["Higher Mind<br/><i>higher-mind</i>"]
    s7["Long-Term Memory<br/><i>long-term-memory</i>"]
    s8["Objectives<br/><i>hold-objectives</i>"]
    s9["Intuition<br/><i>offer-intuition</i>"]
    s10["Context Intake<br/><i>context-intake</i>"]
    s11["planner"]
    s12["delegation"]
    s13["Response Writer<br/><i>response-writer</i>"]
    s14["guidance"]
    s15["ESOI Application<br/><i>esoi-application</i>"]
    s16["Metric Translation<br/><i>metric-translation</i>"]
    s17["Goal Completion<br/><i>goal-completion</i>"]
    s18["Response Quality<br/><i>response-quality</i>"]
    s0 -->|"One signal: proceed, redirect, answer_now, escalate_deep or..."| s5
    s3 -->|"An assembled context view and the ids of the cards it drew..."| s2
    s4 -->|"Hits: unit id, file, first line, score, tokens and text..."| s2
    s4 -->|"Hits: unit id, file, first line, score, tokens and text..."| s3
    s7 -->|"Remembered events that bear on a request"| s6
    s8 -->|"The objectives in progress, their hierarchy and their state"| s6
    s9 -->|"Items offered to the Mind for a request"| s2
    s10 -->|"One view of the information for a request"| s5
    s11 -->|"The pieces of a request, each with the sub-goal it must..."| s5
    s12 -->|"The result of a piece, from the worker that did it"| s5
    s13 -->|"The written plan, request or communication"| s5
    s14 -->|"A nudge for the Planner, or nothing when none is due, and..."| s6
    s15 -->|"Edited specs and metrics, and a run of the improvement loop"| s1
    s16 -->|"A metric with a target value or improvement for a request..."| s1
    s17 -->|"Whether the goal was met, with the reason"| s1
    s18 -->|"The findings against each criterion of the profile; an..."| s1
```
