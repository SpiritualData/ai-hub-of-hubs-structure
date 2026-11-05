# Response Writer

**Purpose:** Write what the Mind outputs for its reader.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [What the Mind sees and does for one request](../README.md) > Response Writer

Part of [What the Mind sees and does for one request](../README.md)

## Response Writer (`response-writer`)

- Out of scope: Judging the response against the quality profile (Response Quality does that) and deciding what to say (the Planner and workers do that).
- Delegates to: response-quality, planner
- Entry call: `hubofhubs.run("response-writer", {'results': [], 'profile': None})`
- Selected implementation: Cited results (`cited_results`)
- Metric: Responses that say what the results hold
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](../../critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](../../critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](../../critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](../../critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](../../critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](../../critical_thinking/goal_completion/goal_completion.py) and 151 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Cited results | `response-writer:cited_results` | Writes the results in order, one paragraph each, then the sources by title and link, and says plainly when a piece was refused or failed. | [`hubofhubs/the_intelligence/mind/response_writer/writer.py`](writer.py) | selected |
| Model synthesis | `response-writer:model_synthesis` | One model call writes the reply from the results under the profile's criteria. | [`hubofhubs/the_intelligence/mind/response_writer/writer.py`](writer.py) |  |

## Metrics

- Responses that say what the results hold (`metric-response-writer`): leader `cited_results`, 44 of 44 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
