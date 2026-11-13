# Structure Watch

**Purpose:** Say where the structure needs attention before more work is built on it, with few tokens and without being asked.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Nervous System](../README.md) > Structure Watch

Part of [Nervous System](../README.md)

## Structure Watch (`structure-watch`)

- Out of scope: Watching a run's steps for irreversible or person-owned acts (the Nervous System's consent gate does that), deciding when it runs (Proactivity does that), ordering what it raises (Prioritization does that), and editing records other than as a recorded, undoable change of structure nobody reviewed (ESOI Application does that).
- Delegates to: judgment-calls, prioritization, proactivity
- Entry call: `hubofhubs.run("structure-watch", ...)`
- Selected implementation: Best tier call (`best_tier_call`)
- Metric: Structure attended to before more is built on it
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 255 more

### Top implementations of Structure Watch

| # | Implementation | Result | Cost per pass | In use |
|---|---|---|---|---|
| 1 | Best tier call (`best_tier_call`) | score 1.00 (18 of 18 cases) | free | selected |
| 2 | Findings only (`findings_only`) | score 0.81 (13 of 18 cases) | free |  |

**How it is scored:** Structure attended to before more is built on it. A planted structural problem is raised and routed to the right party, a clean structure stays silent, an unchanged digest, a run at its ceiling and a switched-off watch make no call, a repeated item is raised again only when worse, and the caps hold.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Best tier call | `structure-watch:best_tier_call` | One call on the best tier over the code-built digest, none when the digest is unchanged, the run is at its ceiling or the watch is off; a reply that is not the JSON asked for falls back to the code's findings. Items are routed through Judgment Calls. | [`hubofhubs/the_intelligence/nervous_system/structure_watch/watch.py`](watch.py) | selected |
| Findings only | `structure-watch:findings_only` | Raises the findings the code computed from the records (at most three, most severe first) with no model call. | [`hubofhubs/the_intelligence/nervous_system/structure_watch/watch.py`](watch.py) |  |

## Metrics

- Structure attended to before more is built on it (`metric-structure-watch`): leader `best_tier_call`, 18 of 18 cases

## Problems

- Work is built on structure that needs attention (`hprob-structure-built-on-before-it-is-attended-to`): New work piles onto a structure that has an experiment past its reevaluation, a solution with several implementations and no metric, a duplicate, a missed reuse or a milestone past its date, and nobody looks at the structure itself until the cost shows.

## Ideals

- Structure attended to before more is built on it (`hideal-structure-is-attended-to-before-more-is-built-on-it`): Look at the structure proactively, with few tokens, and say where it needs attention before the next work is built on it; leave it alone when it is fine.

## Where to go next

- Up: [hubofhubs/the_intelligence/nervous_system](../README.md)
- Intent: [How the AI processes information](../../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
