# Adapting to the humans the system works with

The AI representatives of a team learn each person's way: which authority they carry, when to ask that person and when not to, which priorities the person implies, and how that person wants the work done, from the person's own feedback.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-consciousness:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: Learning when to ask, per person, and translating priorities that are only implied, are opportunities beyond any risk watch: the same step may need a question for one person and none for another. Feedback can then change specs and metrics without a person repeating a correction.

## How the solutions fit together

Consciousness is where the system adapts to the humans and policies it works for. Request Intake takes in what people ask through Intake Sources. Representatives are the AI personas that act for a person, carrying that person's authority, data scope, preferences and quality profile. Prioritization turns the priorities a person states or implies into ESOI. Judgment Calls decides for the person whether to ask, proceed or decline when a step is risky, and how the ask is timed. Feedback Learning proposes edits to specs and metrics, never to prompts. Those edits are applied directly, with no approval step, unless Judgment Calls decides to ask.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Representatives | `the-representatives` | `hubofhubs.run("the-representatives", '')` | Declared authority (`declared_authority`) | Authority that stays with its person |
| Feedback Learning | `feedback-learning` | `hubofhubs.run("feedback-learning", {'person': '', 'feedback': {}})` | none selected | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | `hubofhubs.run("judgment-calls", {'signal': {'signal': 'proceed'}, 'person': ''})` | Per-person severity policy (`severity_policy`) | Asked when a person should be asked |
| Prioritization | `prioritization` | `hubofhubs.run("prioritization", ...)` | none selected | Weights match the priorities the person confirms |
| Request Intake | `request-intake` | `hubofhubs.run("request-intake", {'person': ''})` | Every declared source (`every_declared_source`) | Requests taken in once with their person |

## Problems and ideals

**Problems**

- Asking by one fixed rule (`hprob-ai-asks-on-one-fixed-rule`): The AI asks by a fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve.
- Feedback forgotten (`hprob-feedback-is-forgotten`): A person's correction changes one reply and is forgotten, so the same correction is needed again.
- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People imply their priorities instead of stating them, so an AI weighs everything the same or guesses.
- Requests from unseen places (`hprob-requests-come-from-places-the-system-cannot-see`): People make requests where they already work (a chat, a task list, the action items of a meeting), and a system that only answers one input cannot take them in, so requests are lost, answered twice or answered to the wrong person.

**Ideals**

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- One signal contract (`hideal-one-signal-contract`): The risk watch and the asking judgment share one signal: a risk with its severity and reason, then one decision for one person.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Implied priorities reach ESOI (`hideal-implied-priorities-reach-esoi`): The priorities a person implies are recorded as ESOI milestones and weights.
- Every request taken in once (`hideal-every-request-is-taken-in-once`): A request made anywhere the system listens is taken in once and attached to the person who made it.

## Metrics and their leaders

- Authority that stays with its person (`metric-the-representatives`)
- A correction given once is followed afterwards (`metric-feedback-learning`)
- Asked when a person should be asked (`metric-judgment-calls`): leader `severity_policy`, 72 of 72 cases
- Weights match the priorities the person confirms (`metric-human-prioritization`)
- Requests taken in once with their person (`metric-request-intake`)

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Asking by one fixed rule (`hprob-ai-asks-on-one-fixed-rule`): The AI asks by a fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve.
- Feedback forgotten (`hprob-feedback-is-forgotten`): A person's correction changes one reply and is forgotten, so the same correction is needed again.
- Priorities implied, not stated (`hprob-priorities-are-implied-not-stated`): People imply their priorities instead of stating them, so an AI weighs everything the same or guesses.
- Requests from unseen places (`hprob-requests-come-from-places-the-system-cannot-see`): People make requests where they already work (a chat, a task list, the action items of a meeting), and a system that only answers one input cannot take them in, so requests are lost, answered twice or answered to the wrong person.

### Ideals

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- One signal contract (`hideal-one-signal-contract`): The risk watch and the asking judgment share one signal: a risk with its severity and reason, then one decision for one person.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Implied priorities reach ESOI (`hideal-implied-priorities-reach-esoi`): The priorities a person implies are recorded as ESOI milestones and weights.
- Every request taken in once (`hideal-every-request-is-taken-in-once`): A request made anywhere the system listens is taken in once and attached to the person who made it.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Representatives | `the-representatives` | Declared authority (`declared_authority`) | Authority that stays with its person |
| Feedback Learning | `feedback-learning` | none selected | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | Per-person severity policy (`severity_policy`) | Asked when a person should be asked |
| Prioritization | `prioritization` | none selected | Weights match the priorities the person confirms |
| Request Intake | `request-intake` | Every declared source (`every_declared_source`) | Requests taken in once with their person |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Ask about every risk | `judgment-calls:ask_every_time` | [hubofhubs/consciousness/judgment.py](../consciousness/judgment.py) |  |
| Per-person severity policy | `judgment-calls:severity_policy` | [hubofhubs/consciousness/judgment.py](../consciousness/judgment.py) |  |
| Every declared source | `request-intake:every_declared_source` | [hubofhubs/consciousness/intake.py](../consciousness/intake.py) |  |
| Declared authority | `the-representatives:declared_authority` | [hubofhubs/consciousness/representatives.py](../consciousness/representatives.py) |  |

### Metrics

- Authority that stays with its person (`metric-the-representatives`): `python3 -m pytest tests/test_consciousness.py`
- A correction given once is followed afterwards (`metric-feedback-learning`): `none`
- Asked when a person should be asked (`metric-judgment-calls`): `esoi run judgment_calls --impl severity_policy; esoi run judgment_calls --impl ask_every_time`
- Weights match the priorities the person confirms (`metric-human-prioritization`): `none`
- Requests taken in once with their person (`metric-request-intake`): `python3 -m pytest tests/test_intake.py`
