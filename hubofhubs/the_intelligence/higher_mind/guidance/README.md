# Guidance

**Purpose:** Keep the Planner pointed at the longer-term outcome without taking over the request.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [The long view across requests](../README.md) > Guidance

Part of [The long view across requests](../README.md)

## Guidance (`guidance`)

- Out of scope: Planning (the Planner does that), a person's own preferences (the Representative carries those) and translating implied priorities (Prioritization does that).
- Delegates to: planner, the-representatives, prioritization
- Entry call: `hubofhubs.run("guidance", ...)`
- Selected implementation: Rule gate (`rule_gate`)
- Metric: A nudge that helps the Planner
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 255 more

### Top implementations of Guidance

| # | Implementation | Result | Cost per pass | In use |
|---|---|---|---|---|
| 1 | Rule gate (`rule_gate`) | score 1.00 (24 of 24 cases) | free | selected |
| 2 | Overlap only (`overlap_only`) | score 0.59 (10 of 24 cases) | free |  |
| 3 | Always nudge (`always_nudge`) | score 0.47 (6 of 24 cases) | free |  |

**How it is scored:** A nudge that helps the Planner. A nudge is infrequent and moves the Planner toward the longer-term outcome.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Rule gate | `guidance:rule_gate` | Holds back when the moment calls for the answer alone (urgent, upset, asked to stop, nothing to do with the objectives, raised lately) and otherwise points at the focused or most related objective with one sentence holding its next target and reading, plus the criteria the objective states. | [`hubofhubs/the_intelligence/higher_mind/guidance/nudging.py`](nudging.py) | selected |
| Overlap only | `guidance:overlap_only` | Points at the objective that shares the most words with the request and says nothing when it shares none: retrieval of the objective with no rules about when to hold back. | [`hubofhubs/the_intelligence/higher_mind/guidance/nudging.py`](nudging.py) |  |
| Always nudge | `guidance:always_nudge` | Points at the first objective with a next target on every request. | [`hubofhubs/the_intelligence/higher_mind/guidance/nudging.py`](nudging.py) |  |

## Metrics

- A nudge that helps the Planner (`metric-planner-guidance`): leader `rule_gate`, 24 of 24 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [The long view across requests](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
