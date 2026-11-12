# The long view across requests

**Vision statement:** The AI keeps a long view that spans requests: what it remembers, the objectives it is serving, and an infrequent longer-term nudge for the Planner.

Breadcrumb: [Top](../../../esoi/README.md) > [How the AI processes information](../README.md) > The long view across requests

This sub-intent arises as the implementation `higher-mind:composition` of its parent intent [`the_intelligence`](../README.md). Opportunities: Retention and recall over what the system stores, the live hierarchy of intents and goals, and the nudge each improve on their own measure, so a request is planned in the light of what came before.

## How the solutions fit together

Higher Mind is the long view across requests. Objectives keeps the live hierarchy of intents and goals and their state, as the solution milestones of the person's intents. Which of those matter most to the person is read from Prioritization, so the order of the goals is known to the rest of the system. Long-Term Memory keeps what is remembered and says what bears on a request. Guidance gives an infrequent, longer-term nudge to the planning of a request, and the quality criteria that belong to the context.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Guidance](guidance/README.md) (solution with implementations): Keep the Planner pointed at the longer-term outcome without taking over the request.
- [Long-Term Memory](long_term_memory/README.md) (solution with implementations): Let the AI keep and recall what happened across requests for each subject it serves, a person or a representative, showing each asker only what they may see.
- [Objectives](objectives/README.md) (solution with implementations): Let the AI keep working toward a goal over many requests and know which objective a request serves.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Guidance | `guidance` | `hubofhubs.run("guidance", ...)` | Rule gate (`rule_gate`) | A nudge that helps the Planner |
| Long-Term Memory | `long-term-memory` | `hubofhubs.run("long-term-memory", {'query': 'rust release', 'person': ''})` | File recall (`file_recall`) | A later request uses what an earlier one learned |
| Objectives | `live-objectives` | `hubofhubs.run("live-objectives", '')` | Rolled-up hierarchy and word placement (`rolled_up`) | An objective persists until it is met |

## Problems and ideals

**Problems**

- Long view lost between requests (`hprob-long-view-lost-between-requests`): In many assistants each request starts mostly fresh: what happened before, what stays true and what the AI is working toward are kept only as far as the chat history or a few saved notes reach.

## Metrics and their leaders

- A nudge that helps the Planner (`metric-planner-guidance`): leader `rule_gate`, 24 of 24 cases
- A later request uses what an earlier one learned (`metric-long-term-memory`): leader `file_recall`, 24 of 25 cases
- An objective persists until it is met (`metric-live-objectives`): leader `rolled_up`, 20 of 20 cases

## Where to go next

- Parent intent: [How the AI processes information](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_intelligence/higher_mind/guidance](guidance/README.md), [hubofhubs/the_intelligence/higher_mind/long_term_memory](long_term_memory/README.md), [hubofhubs/the_intelligence/higher_mind/objectives](objectives/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv)

---

## The full record

### Problems

- Long view lost between requests (`hprob-long-view-lost-between-requests`): In many assistants each request starts mostly fresh: what happened before, what stays true and what the AI is working toward are kept only as far as the chat history or a few saved notes reach.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Guidance | `guidance` | Rule gate (`rule_gate`) | A nudge that helps the Planner |
| Long-Term Memory | `long-term-memory` | File recall (`file_recall`) | A later request uses what an earlier one learned |
| Objectives | `live-objectives` | Rolled-up hierarchy and word placement (`rolled_up`) | An objective persists until it is met |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Rule gate | `guidance:rule_gate` | [hubofhubs/the_intelligence/higher_mind/guidance/nudging.py](guidance/nudging.py) |  |
| Overlap only | `guidance:overlap_only` | [hubofhubs/the_intelligence/higher_mind/guidance/nudging.py](guidance/nudging.py) |  |
| Always nudge | `guidance:always_nudge` | [hubofhubs/the_intelligence/higher_mind/guidance/nudging.py](guidance/nudging.py) |  |
| File recall | `long-term-memory:file_recall` | [hubofhubs/the_intelligence/higher_mind/long_term_memory/recall.py](long_term_memory/recall.py) |  |
| Card Store recall | `long-term-memory:card_store_recall` | [hubofhubs/the_intelligence/higher_mind/long_term_memory/recall.py](long_term_memory/recall.py) |  |
| Recent window | `long-term-memory:recent_window` | [hubofhubs/the_intelligence/higher_mind/long_term_memory/recall.py](long_term_memory/recall.py) |  |
| Rolled-up hierarchy and word placement | `live-objectives:rolled_up` | [hubofhubs/the_intelligence/higher_mind/objectives/hierarchy.py](objectives/hierarchy.py) |  |
| Flat list | `live-objectives:flat_list` | [hubofhubs/the_intelligence/higher_mind/objectives/hierarchy.py](objectives/hierarchy.py) |  |

### Metrics

- A nudge that helps the Planner (`metric-planner-guidance`): `esoi run guidance --impl rule_gate; esoi run guidance --impl overlap_only; esoi run guidance --impl always_nudge`
- A later request uses what an earlier one learned (`metric-long-term-memory`): `esoi run long_term_memory --impl file_recall; esoi run long_term_memory --impl card_store_recall; esoi run long_term_memory --impl recent_window`
- An objective persists until it is met (`metric-live-objectives`): `esoi run live_objectives --impl rolled_up; esoi run live_objectives --impl flat_list`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
