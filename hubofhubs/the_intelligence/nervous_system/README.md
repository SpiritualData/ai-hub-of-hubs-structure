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
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/tests/test_decision_check.py`](../critical_thinking/decision_check/tests/test_decision_check.py) and 176 more

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
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
