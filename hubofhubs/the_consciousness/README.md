# Adapting to the humans the system works with

**Vision statement:** The AI system works in alignment with the humans it serves.

Breadcrumb: [Top](../../esoi/README.md) > Adapting to the humans the system works with

This sub-intent arises as the implementation `the-consciousness:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: Learning when to ask, per person, ordering what reaches the person so their scarce attention goes to what unblocks the most work, and translating priorities that are only implied, are opportunities beyond any risk watch: the same step may need a question for one person and none for another. Feedback can then change specs and metrics without a person repeating a correction.

## How the solutions fit together

Consciousness is where the system adapts to the humans and policies it works for. Representatives are the AI personas that act for a person, carrying that person's authority, data scope, preferences and quality profile. Request Intake takes in what people ask through Intake Sources. The interactive entry is Terminal Session: a person types in a plain terminal, each line goes through the front door, and the work and any question are drawn so the next line answers an open question. Prioritization is the one place that orders three things for a person: the work the system is about to start unasked, which Intelligence says is due; the asks that arrive from Judgment Calls once it has decided to ask; and the person's own goals, which Intelligence keeps live. It also turns priorities a person states or implies into ESOI. Judgment Calls decides whether to ask, proceed or decline when a step is risky, and how the ask is timed. Feedback Learning proposes edits to specs and metrics, never to prompts. Those edits are applied directly, with no approval step, unless Judgment Calls decides to ask.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- Feedback Learning (solution with no page of its own, its implementations are in this intent's records): Make a correction given once change behaviour afterwards: propose edits to specs and metrics, which ESOI Application applies directly unless Judgment Calls decides to ask.
- [Judgment Calls](judgment_calls/README.md) (solution with implementations): Ask a person only when that person would want to be asked, and decide how: whether the ask blocks or waits, whether it is batched, what may continue meanwhile, and whether a change to specs or a learning step needs an ask at all (by default it does not).
- [Prioritization](prioritization/README.md) (solution with implementations): Put what competes for a person's attention in the order they would: their work, the asks to them and their goals.
- [Representatives](representatives/README.md) (solution with implementations): Let an AI act for a person the way that person would want, within the authority the person gave: the worker categories allowed, the data scope (whose data the AI may read), the person's asking policy and quality profile.
- [Request Intake](request_intake/README.md) (solution with implementations): Take in every request a person makes, once, from wherever the system listens.
- [Terminal Session](terminal/README.md) (solution with implementations): Let a person converse with the hub in a plain terminal and always see what it is doing and what it asks.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Feedback Learning | `feedback-learning` | `hubofhubs.run("feedback-learning", {'person': '', 'feedback': {}})` | Scoped record edit (`scoped_record_edit`) | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | `hubofhubs.run("judgment-calls", {'signal': {'signal': 'proceed'}, 'person': ''})` | Per-person severity policy (`severity_policy`) | Asked when a person should be asked |
| Prioritization | `prioritization` | `hubofhubs.run("prioritization", ...)` | Stated and carried fields (`stated_fields`) | Work, asks and milestones in the order the stated rules give |
| Representatives | `the-representatives` | `hubofhubs.run("the-representatives", '')` | Declared authority (`declared_authority`) | Authority that stays with its person |
| Request Intake | `request-intake` | `hubofhubs.run("request-intake", {'person': ''})` | Every declared source (`every_declared_source`) | Requests taken in once with their person |
| Terminal Session | `terminal-session` | `hubofhubs.run("terminal-session", {'lines': ['/quit']})` | Line REPL (ahohs chat) (`line_repl`) | Scripted sessions that end right |

## Problems and ideals

**Problems**

- Asking by one fixed rule (`hprob-ai-asks-on-one-fixed-rule`): Most AI assistants decide when to ask by one fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve.
- Feedback forgotten (`hprob-feedback-is-forgotten`): In many assistants a correction changes the next reply but is not kept, so the person has to give it again.
- Requests from unseen places (`hprob-requests-come-from-places-the-system-cannot-see`): People make requests where they already work (a chat, a task list, the action items of a meeting), and a system that only answers one input cannot take them in, so requests are lost, answered twice or answered to the wrong person.
- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People often imply their priorities instead of stating them, so an AI weighs everything the same or guesses.
- Asks reach a person in arrival order (`hprob-asks-arrive-in-arrival-order`): The questions, decisions and approvals an AI puts to a person reach them in the order they arrived, whatever each one unblocks, so the answer that would free five waiting tasks sits behind a question nothing waits on, and a person with many open asks is shown all of them at once.
- A person's milestones are a flat list (`hprob-goals-are-a-flat-list`): The milestones of the solutions of a person's intents (what each solution is to reach next, with its target time and what it depends on) are held as a flat list, so the AI cannot tell which matters most to the person: a milestone others depend on, one with a near target time and one the person said they care most about look alike, and the AI orders its own work and its questions without knowing.
- Unasked work starts in the order it became due (`hprob-unasked-work-starts-in-due-order`): The work the AI is about to start unasked is started in the order it became due, so a daily chore can run before the report the person is waiting for.
- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.

**Ideals**

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- Risk and asking never disagree (`hideal-one-signal-contract`): How risky a step is and whether a person is asked about it never disagree, and a person's correction changes both at once.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Every request taken in once (`hideal-every-request-is-taken-in-once`): A request made anywhere the system listens is taken in once and attached to the person who made it.
- Effort follows what the person cares about (`hideal-implied-priorities-reach-esoi`): The system's effort follows what the person cares about most, including what they only imply.
- A person's attention goes to what frees the most work (`hideal-scarce-attention-goes-to-what-unblocks-most`): A person's attention is scarce, so the AI puts first in front of them the question whose answer frees the most work, and no more at once than they welcome.
- The AI knows which goals matter most (`hideal-the-ai-knows-which-goals-matter-most`): The AI knows which of a person's goals matters most to them, and why, from what they stated, how they reacted, deadlines and what depends on what.
- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.

## Metrics and their leaders

- A correction given once is followed afterwards (`metric-feedback-learning`): leader `scoped_record_edit`, 12 of 12 cases
- Asked when a person should be asked (`metric-judgment-calls`): leader `severity_policy`, 72 of 72 cases
- Work, asks and milestones in the order the stated rules give (`metric-human-prioritization`): leader `stated_fields`, 34 of 34 cases
- Authority that stays with its person (`metric-the-representatives`)
- Requests taken in once with their person (`metric-request-intake`)
- Scripted sessions that end right (`metric-terminal-session`): leader `line_repl`, 14 of 14 cases

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records beside the code: [hubofhubs/the_consciousness/feedback_learning](feedback_learning/README.md), [hubofhubs/the_consciousness/judgment_calls](judgment_calls/README.md), [hubofhubs/the_consciousness/prioritization](prioritization/README.md), [hubofhubs/the_consciousness/representatives](representatives/README.md), [hubofhubs/the_consciousness/request_intake](request_intake/README.md), [hubofhubs/the_consciousness/terminal](terminal/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Asking by one fixed rule (`hprob-ai-asks-on-one-fixed-rule`): Most AI assistants decide when to ask by one fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve.
- Feedback forgotten (`hprob-feedback-is-forgotten`): In many assistants a correction changes the next reply but is not kept, so the person has to give it again.
- Requests from unseen places (`hprob-requests-come-from-places-the-system-cannot-see`): People make requests where they already work (a chat, a task list, the action items of a meeting), and a system that only answers one input cannot take them in, so requests are lost, answered twice or answered to the wrong person.
- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People often imply their priorities instead of stating them, so an AI weighs everything the same or guesses.
- Asks reach a person in arrival order (`hprob-asks-arrive-in-arrival-order`): The questions, decisions and approvals an AI puts to a person reach them in the order they arrived, whatever each one unblocks, so the answer that would free five waiting tasks sits behind a question nothing waits on, and a person with many open asks is shown all of them at once.
- A person's milestones are a flat list (`hprob-goals-are-a-flat-list`): The milestones of the solutions of a person's intents (what each solution is to reach next, with its target time and what it depends on) are held as a flat list, so the AI cannot tell which matters most to the person: a milestone others depend on, one with a near target time and one the person said they care most about look alike, and the AI orders its own work and its questions without knowing.
- Unasked work starts in the order it became due (`hprob-unasked-work-starts-in-due-order`): The work the AI is about to start unasked is started in the order it became due, so a daily chore can run before the report the person is waiting for.
- The hub runs one input per command (`hprob-the-hub-runs-one-input-at-a-time-from-a-command-line`): The hub can be run from a command line one input at a time, and each run starts without the earlier ones, so a person cannot try it or steer it by talking with it, answer a question it asks, or see what it is doing between one line and the next.

### Ideals

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- Risk and asking never disagree (`hideal-one-signal-contract`): How risky a step is and whether a person is asked about it never disagree, and a person's correction changes both at once.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Every request taken in once (`hideal-every-request-is-taken-in-once`): A request made anywhere the system listens is taken in once and attached to the person who made it.
- Effort follows what the person cares about (`hideal-implied-priorities-reach-esoi`): The system's effort follows what the person cares about most, including what they only imply.
- A person's attention goes to what frees the most work (`hideal-scarce-attention-goes-to-what-unblocks-most`): A person's attention is scarce, so the AI puts first in front of them the question whose answer frees the most work, and no more at once than they welcome.
- The AI knows which goals matter most (`hideal-the-ai-knows-which-goals-matter-most`): The AI knows which of a person's goals matters most to them, and why, from what they stated, how they reacted, deadlines and what depends on what.
- Converse with the hub in a plain terminal (`hideal-a-person-can-converse-with-the-hub-in-a-terminal`): A person can converse with the hub in a plain terminal and always see what it is doing and what it asks.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Feedback Learning | `feedback-learning` | Scoped record edit (`scoped_record_edit`) | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | Per-person severity policy (`severity_policy`) | Asked when a person should be asked |
| Prioritization | `prioritization` | Stated and carried fields (`stated_fields`) | Work, asks and milestones in the order the stated rules give |
| Representatives | `the-representatives` | Declared authority (`declared_authority`) | Authority that stays with its person |
| Request Intake | `request-intake` | Every declared source (`every_declared_source`) | Requests taken in once with their person |
| Terminal Session | `terminal-session` | Line REPL (ahohs chat) (`line_repl`) | Scripted sessions that end right |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Kept note | `feedback-learning:kept_note` | [hubofhubs/the_consciousness/feedback_learning/propose.py](feedback_learning/propose.py) |  |
| Scoped record edit | `feedback-learning:scoped_record_edit` | [hubofhubs/the_consciousness/feedback_learning/propose.py](feedback_learning/propose.py) |  |
| Ask about every risk | `judgment-calls:ask_every_time` | [hubofhubs/the_consciousness/judgment_calls/judgment.py](judgment_calls/judgment.py) |  |
| Per-person severity policy | `judgment-calls:severity_policy` | [hubofhubs/the_consciousness/judgment_calls/judgment.py](judgment_calls/judgment.py) |  |
| Stated and carried fields | `prioritization:stated_fields` | [hubofhubs/the_consciousness/prioritization/ordering.py](prioritization/ordering.py) |  |
| As given | `prioritization:as_given` | [hubofhubs/the_consciousness/prioritization/ordering.py](prioritization/ordering.py) |  |
| Declared authority | `the-representatives:declared_authority` | [hubofhubs/the_consciousness/representatives/representatives.py](representatives/representatives.py) |  |
| Every declared source | `request-intake:every_declared_source` | [hubofhubs/the_consciousness/request_intake/intake.py](request_intake/intake.py) |  |
| Line REPL (ahohs chat) | `terminal-session:line_repl` | [hubofhubs/the_consciousness/terminal/repl.py](terminal/repl.py) |  |

### Metrics

- A correction given once is followed afterwards (`metric-feedback-learning`): `esoi run feedback_learning --impl scoped_record_edit; esoi run feedback_learning --impl kept_note`
- Asked when a person should be asked (`metric-judgment-calls`): `esoi run judgment_calls --impl severity_policy; esoi run judgment_calls --impl ask_every_time`
- Work, asks and milestones in the order the stated rules give (`metric-human-prioritization`): `esoi run prioritization --impl stated_fields; esoi run prioritization --impl as_given`
- Authority that stays with its person (`metric-the-representatives`): `python3 -m pytest hubofhubs/the_consciousness/tests/test_consciousness.py`
- Requests taken in once with their person (`metric-request-intake`): `python3 -m pytest tests/test_intake.py`
- Scripted sessions that end right (`metric-terminal-session`): `esoi run terminal_session --impl line_repl`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
