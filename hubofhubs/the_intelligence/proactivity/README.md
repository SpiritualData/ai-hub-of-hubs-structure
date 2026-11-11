# Proactivity

**Purpose:** Let the system start its standing work when it is due, without being asked.

Breadcrumb: [Top](../../../esoi/README.md) > [How the AI processes information](../README.md) > Proactivity

Part of [How the AI processes information](../README.md)

## Proactivity (`proactivity`)

- Out of scope: Doing the work (the flow does that) and deciding whether it may be done unasked (Judgment Calls and the Nervous System do that).
- Delegates to: planner, prioritization, intake-sources
- Entry call: `hubofhubs.run("proactivity", {'schedules': [], 'now': '2026-07-12T09:00:00Z'})`
- Selected implementation: Calendar periods and events (`calendar_and_events`)
- Metric: Schedules due when they should be, Standing work that moves its own metric
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../critical_thinking/decision_check/remainder.py) and 237 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Calendar periods and events | `proactivity:calendar_and_events` | Due by calendar period in the schedule's own zone, on the days and at the time of day of its window (once per occasion, within its grace), by a run requested after the last run, or by an event after the last run for a reactive schedule; an unreadable time fails open to due. | [`hubofhubs/the_intelligence/proactivity/triggers.py`](triggers.py) | selected |
| Elapsed hours | `proactivity:elapsed_hours` | Due when the cadence's hours have passed since the last run. | [`hubofhubs/the_intelligence/proactivity/triggers.py`](triggers.py) |  |
| Standing work standard | `proactivity:standing_work_standard` | A prompt constant of eight points that every unattended recurring run is given and that whoever writes the standing instructions of such a run reads: count acts not reports, act with what the run has, plan around the people as they are, report a blocker once, treat every run as a trial, leave the next step ordered, scale on few tokens, and sample and schedule review. A consumer imports it through the public api. | [`hubofhubs/the_intelligence/proactivity/standing_work.py`](standing_work.py) |  |

## Metrics

- Schedules due when they should be (`metric-proactivity`): leader `calendar_and_events`, 43 of 43 cases
- Standing work that moves its own metric (`metric-standing-work-moves-its-metric`)

## Problems

- The system only reacts (`hprob-system-waits-to-be-asked`): An AI that acts only when asked misses the standing work (a daily review, a weekly report) and the moment something changed, so people must remember to ask.
- Recurring work falls on days and times (`hprob-recurring-work-has-days-and-times`): Standing work for a person often falls on certain days of the week and a time of day in that person's own time zone (a review on weekday mornings, a report on Friday afternoons), and a late start is still worth doing for a while but not forever.
- Standing work spins its wheels (`hprob-standing-work-spins-its-wheels`): Work that repeats unattended drifts into re-reading a number that cannot move, writing briefs and drafts that no one acts on, staging every item for approval and reporting the same missing access each run, so each run looks busy while little outside it changes.

## Ideals

- The system acts on time (`hideal-the-system-acts-on-time`): Standing work happens when it is due, in the person's own time, or when something happens that calls for it, without anyone having to ask.
- Recurring work keeps its days and times (`hideal-recurring-work-keeps-its-days-and-times`): Recurring work starts on the days and at the time of day its person keeps, in their own time zone, once per occasion, and a start that is a little late still counts.
- Standing work changes something outside itself (`hideal-standing-work-changes-something-outside-itself`): Each run of standing work changes something outside itself that its own acts can move within days, and leaves the next step ordered for the next run.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [How the AI processes information](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
