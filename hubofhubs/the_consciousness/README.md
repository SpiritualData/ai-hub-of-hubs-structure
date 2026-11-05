# Adapting to the humans the system works with

The AI system works in alignment with the humans it serves.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-consciousness:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: Learning when to ask, per person, and translating priorities that are only implied, are opportunities beyond any risk watch: the same step may need a question for one person and none for another. Feedback can then change specs and metrics without a person repeating a correction.

## How the solutions fit together

Consciousness is where the system adapts to the humans and policies it works for. Request Intake takes in what people ask through Intake Sources. Representatives are the AI personas that act for a person, carrying that person's authority, data scope, preferences and quality profile. Prioritization turns the priorities a person states or implies into ESOI and puts the work that competes for the person's attention in order. Judgment Calls decides for the person whether to ask, proceed or decline when a step is risky, and how the ask is timed. Feedback Learning proposes edits to specs and metrics, never to prompts. Those edits are applied directly, with no approval step, unless Judgment Calls decides to ask.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Feedback Learning | `feedback-learning` | `hubofhubs.run("feedback-learning", {'person': '', 'feedback': {}})` | none selected | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | `hubofhubs.run("judgment-calls", {'signal': {'signal': 'proceed'}, 'person': ''})` | Per-person severity policy (`severity_policy`) | Asked when a person should be asked |
| Prioritization | `prioritization` | `hubofhubs.run("prioritization", ...)` | Stated and carried fields (`stated_fields`) | Candidates in the order the production rules give |
| Representatives | `the-representatives` | `hubofhubs.run("the-representatives", '')` | Declared authority (`declared_authority`) | Authority that stays with its person |
| Request Intake | `request-intake` | `hubofhubs.run("request-intake", {'person': ''})` | Every declared source (`every_declared_source`) | Requests taken in once with their person |

## Problems and ideals

**Problems**

- Asking by one fixed rule (`hprob-ai-asks-on-one-fixed-rule`): Most AI assistants decide when to ask by one fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve.
- Feedback forgotten (`hprob-feedback-is-forgotten`): In many assistants a correction changes the next reply but is not kept, so the person has to give it again.
- Requests from unseen places (`hprob-requests-come-from-places-the-system-cannot-see`): People make requests where they already work (a chat, a task list, the action items of a meeting), and a system that only answers one input cannot take them in, so requests are lost, answered twice or answered to the wrong person.
- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People often imply their priorities instead of stating them, so an AI weighs everything the same or guesses.

**Ideals**

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- Risk and asking never disagree (`hideal-one-signal-contract`): How risky a step is and whether a person is asked about it never disagree, and a person's correction changes both at once.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Every request taken in once (`hideal-every-request-is-taken-in-once`): A request made anywhere the system listens is taken in once and attached to the person who made it.
- Effort follows what the person cares about (`hideal-implied-priorities-reach-esoi`): The system's effort follows what the person cares about most, including what they only imply.

## Metrics and their leaders

- A correction given once is followed afterwards (`metric-feedback-learning`)
- Asked when a person should be asked (`metric-judgment-calls`): leader `severity_policy`, 72 of 72 cases
- Candidates in the order the production rules give (`metric-human-prioritization`): leader `stated_fields`, 13 of 13 cases
- Authority that stays with its person (`metric-the-representatives`)
- Requests taken in once with their person (`metric-request-intake`)

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records beside the code: [hubofhubs/the_consciousness/judgment_calls](judgment_calls/README.md), [hubofhubs/the_consciousness/prioritization](prioritization/README.md), [hubofhubs/the_consciousness/representatives](representatives/README.md), [hubofhubs/the_consciousness/request_intake](request_intake/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Asking by one fixed rule (`hprob-ai-asks-on-one-fixed-rule`): Most AI assistants decide when to ask by one fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve.
- Feedback forgotten (`hprob-feedback-is-forgotten`): In many assistants a correction changes the next reply but is not kept, so the person has to give it again.
- Requests from unseen places (`hprob-requests-come-from-places-the-system-cannot-see`): People make requests where they already work (a chat, a task list, the action items of a meeting), and a system that only answers one input cannot take them in, so requests are lost, answered twice or answered to the wrong person.
- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People often imply their priorities instead of stating them, so an AI weighs everything the same or guesses.

### Ideals

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- Risk and asking never disagree (`hideal-one-signal-contract`): How risky a step is and whether a person is asked about it never disagree, and a person's correction changes both at once.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Every request taken in once (`hideal-every-request-is-taken-in-once`): A request made anywhere the system listens is taken in once and attached to the person who made it.
- Effort follows what the person cares about (`hideal-implied-priorities-reach-esoi`): The system's effort follows what the person cares about most, including what they only imply.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Feedback Learning | `feedback-learning` | none selected | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | Per-person severity policy (`severity_policy`) | Asked when a person should be asked |
| Prioritization | `prioritization` | Stated and carried fields (`stated_fields`) | Candidates in the order the production rules give |
| Representatives | `the-representatives` | Declared authority (`declared_authority`) | Authority that stays with its person |
| Request Intake | `request-intake` | Every declared source (`every_declared_source`) | Requests taken in once with their person |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Ask about every risk | `judgment-calls:ask_every_time` | [hubofhubs/the_consciousness/judgment_calls/judgment.py](judgment_calls/judgment.py) |  |
| Per-person severity policy | `judgment-calls:severity_policy` | [hubofhubs/the_consciousness/judgment_calls/judgment.py](judgment_calls/judgment.py) |  |
| Stated and carried fields | `prioritization:stated_fields` | [hubofhubs/the_consciousness/prioritization/ordering.py](prioritization/ordering.py) |  |
| As given | `prioritization:as_given` | [hubofhubs/the_consciousness/prioritization/ordering.py](prioritization/ordering.py) |  |
| Declared authority | `the-representatives:declared_authority` | [hubofhubs/the_consciousness/representatives/representatives.py](representatives/representatives.py) |  |
| Every declared source | `request-intake:every_declared_source` | [hubofhubs/the_consciousness/request_intake/intake.py](request_intake/intake.py) |  |

### Metrics

- A correction given once is followed afterwards (`metric-feedback-learning`): `none`
- Asked when a person should be asked (`metric-judgment-calls`): `esoi run judgment_calls --impl severity_policy; esoi run judgment_calls --impl ask_every_time`
- Candidates in the order the production rules give (`metric-human-prioritization`): `esoi run prioritization --impl stated_fields; esoi run prioritization --impl as_given`
- Authority that stays with its person (`metric-the-representatives`): `python3 -m pytest hubofhubs/the_consciousness/tests/test_consciousness.py`
- Requests taken in once with their person (`metric-request-intake`): `python3 -m pytest tests/test_intake.py`
