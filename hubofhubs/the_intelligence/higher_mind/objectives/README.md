# Objectives

**Purpose:** Let the AI keep working toward a goal over many requests and know which objective a request serves.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [The long view across requests](../README.md) > Objectives

Part of [The long view across requests](../README.md)

## Objectives (`live-objectives`)

- Out of scope: Turning a request into a metric (Metric Translation does that) nudging the Planner (Guidance does that) and deciding which milestones matter most to the person (Prioritization does that).
- Delegates to: metric-translation, guidance, prioritization
- Entry call: `hubofhubs.run("live-objectives", '')`
- Selected implementation: Rolled-up hierarchy and word placement (`rolled_up`)
- Metric: An objective persists until it is met
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 184 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Rolled-up hierarchy and word placement | `live-objectives:rolled_up` | Reads the recorded objectives as a hierarchy: an objective's progress is the share of its units met, its units being its own criteria and its children (each counting its own progress), so a goal rolls up to its parent; it is met only when every unit is, and one with no criteria and no children is met only when it says so. A request is placed under the live (not met) objective whose title and criteria share the most meaningful words with it, the deeper one on a tie, and the answer carries the path from the top. | [`hubofhubs/the_intelligence/higher_mind/objectives/hierarchy.py`](hierarchy.py) | selected |
| Flat list | `live-objectives:flat_list` | Returns the objectives as listed with no roll-up (state and progress from each one's own criteria only) and places a request only under the first top-level objective that shares a word. | [`hubofhubs/the_intelligence/higher_mind/objectives/hierarchy.py`](hierarchy.py) |  |

## Metrics

- An objective persists until it is met (`metric-live-objectives`): leader `rolled_up`, 20 of 20 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [The long view across requests](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
