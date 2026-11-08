# Prioritization

**Purpose:** Put what competes for a person's attention in the order they would: their work, the asks to them and their goals.

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Prioritization

Part of [Adapting to the humans the system works with](../README.md)

## Prioritization (`prioritization`)

- Out of scope: Whether an ask is made at all (Judgment Calls decides that), holding the goals and their progress (Objectives does that), carrying the person's preferences (Representatives do that), turning a request into a metric (Metric Translation does that), long-term nudges (Guidance does that), deciding what is due (Proactivity does that) and whether work may be done unasked (Judgment Calls does that).
- Delegates to: the-representatives, metric-translation, guidance, proactivity, judgment-calls, live-objectives
- Entry call: `hubofhubs.run("prioritization", ...)`
- Selected implementation: Stated and carried fields (`stated_fields`)
- Metric: Work, asks and milestones in the order the stated rules give
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/communication.py`](../communication.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](../feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](../feedback_learning/interface.py), [`hubofhubs/the_consciousness/feedback_learning/propose.py`](../feedback_learning/propose.py), [`hubofhubs/the_consciousness/feedback_learning/tests/test_feedback_learning.py`](../feedback_learning/tests/test_feedback_learning.py), [`hubofhubs/the_consciousness/flow.py`](../flow.py) and 35 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Stated and carried fields | `prioritization:stated_fields` | Orders the candidates by what the person stated and the fields the data carries: what the person pinned first and deferred last, what their feedback implies, the kind in the order the person gave, a blocked item after the unblocked, the person's own rank (ranked first, unranked after), the earlier deadline, the older ask, the more people waiting and the longer since a nudge. Each place has a reason in words and a weighted milestone. | [`hubofhubs/the_consciousness/prioritization/ordering.py`](ordering.py) | selected |
| As given | `prioritization:as_given` | Keeps the order the candidates arrive in and reads nothing from them. | [`hubofhubs/the_consciousness/prioritization/ordering.py`](ordering.py) |  |

## Metrics

- Work, asks and milestones in the order the stated rules give (`metric-human-prioritization`): leader `stated_fields`, 34 of 34 cases

## Problems

- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People often imply their priorities instead of stating them, so an AI weighs everything the same or guesses.
- Asks reach a person in arrival order (`hprob-asks-arrive-in-arrival-order`): The questions, decisions and approvals an AI puts to a person reach them in the order they arrived, whatever each one unblocks, so the answer that would free five waiting tasks sits behind a question nothing waits on, and a person with many open asks is shown all of them at once.
- A person's milestones are a flat list (`hprob-goals-are-a-flat-list`): The milestones of the solutions of a person's intents (what each solution is to reach next, with its target time and what it depends on) are held as a flat list, so the AI cannot tell which matters most to the person: a milestone others depend on, one with a near target time and one the person said they care most about look alike, and the AI orders its own work and its questions without knowing.
- Unasked work starts in the order it became due (`hprob-unasked-work-starts-in-due-order`): The work the AI is about to start unasked is started in the order it became due, so a daily chore can run before the report the person is waiting for.

## Ideals

- Effort follows what the person cares about (`hideal-implied-priorities-reach-esoi`): The system's effort follows what the person cares about most, including what they only imply.
- A person's attention goes to what frees the most work (`hideal-scarce-attention-goes-to-what-unblocks-most`): A person's attention is scarce, so the AI puts first in front of them the question whose answer frees the most work, and no more at once than they welcome.
- The AI knows which goals matter most (`hideal-the-ai-knows-which-goals-matter-most`): The AI knows which of a person's goals matters most to them, and why, from what they stated, how they reacted, deadlines and what depends on what.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
