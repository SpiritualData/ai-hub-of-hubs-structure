# Vendor Model Caller

*ESOI records kept beside the code in `hubofhubs/the_world/model_plumbing/vendor_model_caller`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

Every part asks a model through one path: the tier is chosen by measurement and the vendor behind it can change without any part noticing.

These are the solutions of [Asking a model through one measured path](../README.md).

## How the solutions fit together

Model Plumbing is how every part asks a model. Model Tier Chooser picks, per tier, the model that did the most passing work per unit of cost. Vendor Model Caller asks that vendor and steps to the next provider when one fails.

## Vendor Model Caller (`vendor-model-caller`)

Reach one vendor's model, and step to the next provider when one fails.

- Entry call: `hubofhubs.run("vendor-model-caller", ...)`
- Selected implementation: Multi-provider router (`multi_provider`)
- Metric: Provider failover
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 122 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Anthropic provider | `vendor-model-caller:anthropic` | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/anthropic.py`](anthropic.py) |  |
| DeepSeek provider | `vendor-model-caller:deepseek` | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/openai.py`](openai.py) |  |
| Gemini provider | `vendor-model-caller:gemini` | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/gemini.py`](gemini.py) |  |
| Multi-provider router | `vendor-model-caller:multi_provider` | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/router.py`](router.py) | selected |
| OpenAI provider | `vendor-model-caller:openai` | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/openai.py`](openai.py) |  |
| Claude Code CLI | `vendor-model-caller:claude_cli` | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/claude_cli.py`](claude_cli.py) |  |

## Metrics

- Provider failover (`metric-vendor-model-caller`): leader `multi_provider`, 30 of 30 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Asking a model through one measured path](../README.md)
- Repository: [top README](../../../../README.md)
