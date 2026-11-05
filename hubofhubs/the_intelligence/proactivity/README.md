# Proactivity

**Purpose:** Let the system start its standing work when it is due, without being asked.

Breadcrumb: [Top](../../../esoi/README.md) > [How the AI processes information](../README.md) > Proactivity

Part of [How the AI processes information](../README.md)

## Proactivity (`proactivity`)

- Out of scope: Doing the work (the flow does that) and deciding whether it may be done unasked (Judgment Calls and the Nervous System do that).
- Delegates to: planner, prioritization, intake-sources
- Entry call: `hubofhubs.run("proactivity", {'schedules': [], 'now': '2026-07-12T09:00:00Z'})`
- Selected implementation: Calendar periods and events (`calendar_and_events`)
- Metric: Schedules due when they should be
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../critical_thinking/goal_completion/goal_completion.py) and 151 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Calendar periods and events | `proactivity:calendar_and_events` | Due by calendar period in the schedule's own zone, by a run requested after the last run, or by an event after the last run for a reactive schedule; an unreadable time fails open to due. | [`hubofhubs/the_intelligence/proactivity/triggers.py`](triggers.py) | selected |
| Elapsed hours | `proactivity:elapsed_hours` | Due when the cadence's hours have passed since the last run. | [`hubofhubs/the_intelligence/proactivity/triggers.py`](triggers.py) |  |

## Metrics

- Schedules due when they should be (`metric-proactivity`): leader `calendar_and_events`, 18 of 18 cases

## Problems

- The system only reacts (`hprob-system-waits-to-be-asked`): An AI that acts only when asked misses the standing work (a daily review, a weekly report) and the moment something changed, so people must remember to ask.

## Ideals

- The system acts on time (`hideal-the-system-acts-on-time`): Standing work happens when it is due, in the person's own time, or when something happens that calls for it, without anyone having to ask.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [How the AI processes information](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
