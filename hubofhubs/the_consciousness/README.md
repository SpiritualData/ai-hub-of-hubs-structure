# Adapting to the humans the system works with

The AI representatives of a team learn each person's way: which authority they carry, when to ask that person and when not to, which priorities the person implies, and how that person wants the work done, from the person's own feedback.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-consciousness:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: Learning when to ask, per person, and translating priorities that are only implied, are opportunities beyond any risk watch: the same step may need a question for one person and none for another. Feedback can then change specs and metrics without a person repeating a correction.

## How the solutions fit together

Consciousness is where the system adapts to the humans and policies it works for. Representatives are the AI personas that act for a person, carrying that person's authority, preferences and quality profile. Prioritization turns the priorities a person states or implies into ESOI. Judgment Calls decides for the person whether to ask, proceed or decline when a step is risky. Feedback Learning applies the person's feedback to specs and metrics, never to prompts.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Representatives | `ai-representatives` | `hubofhubs.run("ai-representatives", {'person': ''})` | none selected | A representative acts as its person would want |
| Feedback Learning | `feedback-learning` | `hubofhubs.run("feedback-learning", {'person': '', 'feedback': {}})` | none selected | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | `hubofhubs.run("judgment-calls", {'signal': {'signal': 'proceed'}, 'person': ''})` | none selected | The decision matches the person's choice |
| Prioritization | `prioritization` | `hubofhubs.run("prioritization", ...)` | none selected | Weights match the priorities the person confirms |

## Problems and ideals

**Problems**

- The AI asks by a fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve. (`hprob-ai-asks-on-one-fixed-rule`)
- A person's correction changes one reply and is forgotten, so the same correction is needed again. (`hprob-feedback-is-forgotten`)
- People imply their priorities instead of stating them, so an AI weighs everything the same or guesses. (`hprob-priorities-are-implied-not-stated`)

**Ideals**

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- One signal contract (`hideal-one-signal-contract`): The risk watch and the asking judgment share one signal: a risk with its severity and reason, then one decision for one person.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Implied priorities reach ESOI (`hideal-implied-priorities-reach-esoi`): The priorities a person implies are recorded as ESOI milestones and weights.

## Metrics and their leaders

- A representative acts as its person would want (`metric-ai-representatives`)
- A correction given once is followed afterwards (`metric-feedback-learning`)
- The decision matches the person's choice (`metric-judgment-calls`)
- Weights match the priorities the person confirms (`metric-prioritization`)

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- The AI asks by a fixed rule, so one person is interrupted for steps they would have allowed and another is surprised by steps they would have wanted to approve. (`hprob-ai-asks-on-one-fixed-rule`)
- A person's correction changes one reply and is forgotten, so the same correction is needed again. (`hprob-feedback-is-forgotten`)
- People imply their priorities instead of stating them, so an AI weighs everything the same or guesses. (`hprob-priorities-are-implied-not-stated`)

### Ideals

- Asked only when wanted (`hideal-asked-only-when-the-person-would-want-it`): An AI representative asks a person when that person would want to be asked, and otherwise proceeds or declines.
- One signal contract (`hideal-one-signal-contract`): The risk watch and the asking judgment share one signal: a risk with its severity and reason, then one decision for one person.
- Feedback changes behaviour (`hideal-feedback-changes-behaviour`): A correction given once is followed afterwards, for the person who gave it.
- Implied priorities reach ESOI (`hideal-implied-priorities-reach-esoi`): The priorities a person implies are recorded as ESOI milestones and weights.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Representatives | `ai-representatives` | none selected | A representative acts as its person would want |
| Feedback Learning | `feedback-learning` | none selected | A correction given once is followed afterwards |
| Judgment Calls | `judgment-calls` | none selected | The decision matches the person's choice |
| Prioritization | `prioritization` | none selected | Weights match the priorities the person confirms |

### Metrics

- A representative acts as its person would want (`metric-ai-representatives`): `none`
- A correction given once is followed afterwards (`metric-feedback-learning`): `none`
- The decision matches the person's choice (`metric-judgment-calls`): `none`
- Weights match the priorities the person confirms (`metric-prioritization`): `none`
