# Vendor Model Caller

**Purpose:** Reach one vendor's model, and step to the next provider when one fails.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Asking a model through one measured path](../README.md) > Vendor Model Caller

Part of [Asking a model through one measured path](../README.md)

## Vendor Model Caller (`vendor-model-caller`)

- Out of scope: Choosing the tier (the Model Tier Chooser does that) and the wording of the question (each part does that).
- Delegates to: model-tier-chooser
- Entry call: `hubofhubs.run("vendor-model-caller", ...)`
- Selected implementation: Multi-provider router (`multi_provider`)
- Metric: Provider failover
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 141 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Anthropic provider | `vendor-model-caller:anthropic` | Plans, answers, searches the web and lists models through the Anthropic SDK. | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/anthropic.py`](anthropic.py) |  |
| DeepSeek provider | `vendor-model-caller:deepseek` | DeepSeek's OpenAI-compatible API through the OpenAI adapter, thinking off by default. | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/openai.py`](openai.py) |  |
| Gemini provider | `vendor-model-caller:gemini` | Plans, answers, searches with Google Search grounding, fetches URLs and lists models through the Google SDK. | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/gemini.py`](gemini.py) |  |
| Multi-provider router | `vendor-model-caller:multi_provider` | Routes each call to the provider that serves its model, and steps to a fallback model on a quota, billing, timeout or outage error. | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/router.py`](router.py) | selected |
| OpenAI provider | `vendor-model-caller:openai` | Plans, answers and lists models over the OpenAI chat API, or any compatible endpoint by base url. | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/openai.py`](openai.py) |  |
| Claude Code CLI | `vendor-model-caller:claude_cli` | Asks Claude through the claude program on a Claude Code subscription, with no API key. | [`hubofhubs/the_world/model_plumbing/vendor_model_caller/claude_cli.py`](claude_cli.py) |  |

## Metrics

- Provider failover (`metric-vendor-model-caller`): leader `multi_provider`, 30 of 30 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Asking a model through one measured path](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
