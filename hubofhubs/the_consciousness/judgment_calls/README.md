# Judgment Calls

**Purpose:** Ask a person only when that person would want to be asked, and decide how: whether the ask blocks or waits, whether it is batched, what may continue meanwhile, and whether a change to specs or a learning step needs an ask at all (by default it does not).

Breadcrumb: [Top](../../../esoi/README.md) > [Adapting to the humans the system works with](../README.md) > Judgment Calls

Part of [Adapting to the humans the system works with](../README.md)

## Judgment Calls (`judgment-calls`)

- Out of scope: Raising the risk signal (the Nervous System does that) and learning the person's thresholds from feedback (Feedback Learning does that) and the order and batch of the asks it decides to make (Prioritization does that).
- Delegates to: nervous-system, feedback-learning, prioritization
- Entry call: `hubofhubs.run("judgment-calls", {'signal': {'signal': 'proceed'}, 'person': ''})`
- Selected implementation: Per-person severity policy (`severity_policy`)
- Metric: Asked when a person should be asked
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../../../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](../__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/__init__.py`](../ai_session_experience/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__init__.py`](../ai_session_experience/acp_agent/__init__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/__main__.py`](../ai_session_experience/acp_agent/__main__.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/mapping.py`](../ai_session_experience/acp_agent/mapping.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/server.py`](../ai_session_experience/acp_agent/server.py), [`hubofhubs/the_consciousness/ai_session_experience/acp_agent/tests/test_acp_agent.py`](../ai_session_experience/acp_agent/tests/test_acp_agent.py) and 172 more

### Top implementations of Judgment Calls

| # | Implementation | Result | Cost per pass | In use |
|---|---|---|---|---|
| 1 | Per-person severity policy (`severity_policy`) | 100% (72 of 72 cases) | free | selected |
| 2 | Ask about every risk (`ask_every_time`) | 94% (68 of 72 cases) | free |  |

**How it is scored:** Asked when a person should be asked. Consent is kept for each person: for a risk signal or a stopped flow the decision is to ask when a person should authorize and to proceed otherwise, and a step that needs the person never proceeds without that decision.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Ask about every risk | `judgment-calls:ask_every_time` | Asks, blocking, about any step that carries any risk, whoever the person is. | [`hubofhubs/the_consciousness/judgment_calls/judgment.py`](judgment.py) |  |
| Per-person severity policy | `judgment-calls:severity_policy` | Proceeds up to the severity a person set, declines from the severity they set and asks in between, to whom they named, with the timing the severity calls for (a medium risk waits and is batched while safe work continues, a high one blocks). | [`hubofhubs/the_consciousness/judgment_calls/judgment.py`](judgment.py) | selected |

## Metrics

- Asked when a person should be asked (`metric-judgment-calls`): leader `severity_policy`, 72 of 72 cases

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Adapting to the humans the system works with](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
