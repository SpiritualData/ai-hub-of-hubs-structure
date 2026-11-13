# Nervous System

**Purpose:** Send one risk signal, a severity and a reason, before irreversible or person-owned steps, without slowing ordinary work and without routing.

Breadcrumb: [Top](../../../esoi/README.md) > [How the AI processes information](../README.md) > Nervous System

Part of [How the AI processes information](../README.md)

## Nervous System (`nervous-system`)

- Out of scope: Deciding whether to ask a particular person (Judgment Calls does that), routing a run (the Planner and Delegation do that) and carrying out the step (the tools do that).
- Delegates to: judgment-calls
- Entry call: `hubofhubs.run("nervous-system", 'delete the old backup folder')`
- Selected implementation: Consent gate (`consent_gate`)
- Metric: Risky steps stopped, ordinary steps let through, Guard marginal value
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../critical_thinking/decision_check/remainder.py) and 255 more

### Top implementations of Nervous System

| # | Implementation | Result | Cost per pass | In use |
|---|---|---|---|---|
| 1 | `two_stage` | 94% (34 of 36 cases) | $0.0000 |  |
| 2 | `overseer` | 92% (33 of 36 cases) | $0.0001 |  |
| 3 | Consent gate (`consent_gate`) | score 0.74 (38 of 60 cases) | free | selected |

The one in use is chosen at the deciding stage of the cascade (see the leaderboard), which can differ from the latest run ranked here.

1 more compared; the full list is in the results log.

**How it is scored:** Risky steps stopped, ordinary steps let through. A step a person should authorize is stopped and an ordinary step is let through.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## One level below

- [Structure Watch](structure_watch/README.md) (solution with implementations): Say where the structure needs attention before more work is built on it, with few tokens and without being asked.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Consent gate | `nervous-system:consent_gate` | Reads a step by rule, with no model call, and sends one risk signal: high for a step that pays, sends outward, deletes, publishes or uses a credential, medium for a step the rules cannot classify, none for plain reading. | [`hubofhubs/the_intelligence/nervous_system/consent_gate.py`](consent_gate.py) | selected |

## Metrics

- Risky steps stopped, ordinary steps let through (`metric-nervous-system`): leader `two_stage`, 34 of 36 cases
- Guard marginal value (`metric-guard-marginal-value-over-native-and-harness`)

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [How the AI processes information](../README.md)
- Down: [hubofhubs/the_intelligence/nervous_system/structure_watch](structure_watch/README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
