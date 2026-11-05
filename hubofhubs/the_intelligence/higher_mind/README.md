# The long view across requests

The AI keeps a long view that spans requests: what it remembers, the objectives it is serving, and an infrequent longer-term nudge for the Planner.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `higher-mind:composition` of its parent intent [`the_intelligence`](../README.md). Opportunities: Retention and recall over what the system stores, the live hierarchy of intents and goals, and the nudge each improve on their own measure, so a request is planned in the light of what came before.

## How the solutions fit together

Higher Mind is the long view across requests. Objectives keeps the live hierarchy of intents and goals and their state. Long-Term Memory keeps what is remembered and says what bears on a request. Guidance gives an infrequent, longer-term nudge to the planning of a request, and the quality criteria that belong to the context.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Long-Term Memory | `long-term-memory` | `hubofhubs.run("long-term-memory", {'query': 'rust release', 'person': ''})` | none selected | A later request uses what an earlier one learned |
| Objectives | `live-objectives` | `hubofhubs.run("live-objectives", '')` | none selected | An objective persists until it is met |
| Guidance | `guidance` | `hubofhubs.run("guidance", ...)` | none selected | A nudge that helps the Planner |

## Problems and ideals

**Problems**

- Long view lost between requests (`hprob-long-view-lost-between-requests`): In many assistants each request starts mostly fresh: what happened before, what stays true and what the AI is working toward are kept only as far as the chat history or a few saved notes reach.

## Metrics and their leaders

- A later request uses what an earlier one learned (`metric-long-term-memory`)
- An objective persists until it is met (`metric-live-objectives`)
- A nudge that helps the Planner (`metric-planner-guidance`)

## Where to go next

- Parent intent: [How the AI processes information](../README.md)
- Repository: [top README](../../../README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Long view lost between requests (`hprob-long-view-lost-between-requests`): In many assistants each request starts mostly fresh: what happened before, what stays true and what the AI is working toward are kept only as far as the chat history or a few saved notes reach.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Long-Term Memory | `long-term-memory` | none selected | A later request uses what an earlier one learned |
| Objectives | `live-objectives` | none selected | An objective persists until it is met |
| Guidance | `guidance` | none selected | A nudge that helps the Planner |

### Metrics

- A later request uses what an earlier one learned (`metric-long-term-memory`): `none`
- An objective persists until it is met (`metric-live-objectives`): `none`
- A nudge that helps the Planner (`metric-planner-guidance`): `none`
