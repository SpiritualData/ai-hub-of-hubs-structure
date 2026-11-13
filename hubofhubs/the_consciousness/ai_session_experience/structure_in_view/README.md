# Structure In View

**Purpose:** Let a person see which solutions the AI is working on and what each sub-agent does there, on any interface, with detail only when they look for it.

Breadcrumb: [Top](../../../../esoi/README.md) > [Adapting to the humans the system works with](../../README.md) > [Working with the AI while it works](../README.md) > Structure In View

Part of [Working with the AI while it works](../README.md)

## Structure In View (`structure-in-view`)

- Out of scope: Drawing the tree on a surface (Terminal Experience, Frontend Interface), choosing which solution a sub-agent works on (Delegation and the solution workers), editing records, and running metrics.
- Entry call: `hubofhubs.run("structure-in-view", ...)`
- Selected implementation: Agents arranged by solution, records read on request (`event_tree`)
- Metric: Right solution per sub-agent, detail only when opened
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__init__.py`](../acp_agent/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__main__.py`](../acp_agent/__main__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/mapping.py`](../acp_agent/mapping.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/server.py`](../acp_agent/server.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/tests/test_acp_agent.py`](../acp_agent/tests/test_acp_agent.py) and 172 more

### Top implementations of Structure In View

| # | Implementation | Result | Cost per pass | In use |
|---|---|---|---|---|
| 1 | Agents arranged by solution, records read on request (`event_tree`) | score 1.00 (20 of 20 cases) | free | selected |

**How it is scored:** Right solution per sub-agent, detail only when opened. The tree shows each sub-agent on the solution it works on in the right hierarchy, stays free of field detail until a solution is opened, then carries that solution's named fields and connections, and an unknown solution is handled.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Agents arranged by solution, records read on request | `structure-in-view:event_tree` | Folds the events into agents, places each solution under the solution of its nearest ancestor agent, and for an opened solution reads its fields and connections from the records tables (esoi.read_tree) with the latest recorded result of its authoritative metric. | [`hubofhubs/the_consciousness/ai_session_experience/structure_in_view/tree.py`](tree.py) | selected |
| Whole delegation tree from the records (not built) | `structure-in-view:records_overlay` | Would draw the full hierarchy of the solution being worked on from delegates_to, and mark the solutions an agent is on, so a person sees the part not started yet. | no code yet |  |

## Metrics

- Right solution per sub-agent, detail only when opened (`metric-structure-in-view`): leader `event_tree`, 20 of 20 cases

## Problems

- The person cannot see how structure is in the work (`hprob-the-person-cannot-see-how-structure-is-in-the-work`): When sub-agents work on specific solutions, the person cannot tell which solutions are being worked on, which sub-agent is on which, what each does, or what a solution is for and how it connects, so the structure that guides the work is invisible while it runs.

## Ideals

- Structure in view, detail one action away (`hideal-structure-is-in-view-and-detail-is-one-action-away`): A person sees at a glance which solutions the AI is working on and what each sub-agent does there, and reaches a solution's fields and connections only by asking.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Working with the AI while it works](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
