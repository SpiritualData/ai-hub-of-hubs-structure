# Asking a model through one measured path

**Vision statement:** Every part asks a model through one path: the tier is chosen by measurement and the vendor behind it can change without any part noticing.

Breadcrumb: [Top](../../../esoi/README.md) > [Awareness of the outside and interaction with it](../README.md) > Asking a model through one measured path

This sub-intent arises as the implementation `model-plumbing:via_vendor` of its parent intent [`the_world`](../README.md). Opportunities: New models, vendors and prices appear outside the system, so the tier choice and the vendor adapters are improved by what is measured about them and not by what was configured once.

## How the solutions fit together

Model Plumbing is how every part asks a model. Model Tier Chooser picks, per tier, the model that did the most passing work per unit of cost. Vendor Model Caller asks that vendor and steps to the next provider when one fails.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Model Tier Chooser](model_tier_chooser/README.md) (solution with implementations): Pick, for each model tier, the model that does the most passing work per cost.
- [Vendor Model Caller](vendor_model_caller/README.md) (solution with implementations): Reach one vendor's model, and step to the next provider when one fails.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Model Tier Chooser | `model-tier-chooser` | `hubofhubs.run("model-tier-chooser", {'available': ['anthropic']})` | Passing work per cost selector (`tier_selector`) | Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer |
| Vendor Model Caller | `vendor-model-caller` | `hubofhubs.run("vendor-model-caller", ...)` | Multi-provider router (`multi_provider`) | Provider failover |

## Problems and ideals

**Problems**

- Every part picks its own model (`hprob-every-part-picks-its-own-model`): When each part that needs a model chooses and calls it its own way, tier choice, cost and failover are repeated in each part and drift apart.

## Metrics and their leaders

- Tier choice by passing work per cost (`metric-model-tier-chooser`): leader `tier_selector`, 36 of 36 cases
- Tier passing work per cost (`metric-tier-passing-work-per-cost`)
- Model quality on hard maths (`metric-model-quality`): leader `deepseek_v4_pro`, 3 of 3 cases
- Vendor arms answer (`metric-vendor-answers`): leader `claude_cli`, 3 of 3 cases
- Provider failover (`metric-vendor-model-caller`): leader `multi_provider`, 30 of 30 cases

## Where to go next

- Parent intent: [Awareness of the outside and interaction with it](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_world/model_plumbing/model_tier_chooser](model_tier_chooser/README.md), [hubofhubs/the_world/model_plumbing/vendor_model_caller](vendor_model_caller/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv)

---

## The full record

### Problems

- Every part picks its own model (`hprob-every-part-picks-its-own-model`): When each part that needs a model chooses and calls it its own way, tier choice, cost and failover are repeated in each part and drift apart.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Model Tier Chooser | `model-tier-chooser` | Passing work per cost selector (`tier_selector`) | Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer |
| Vendor Model Caller | `vendor-model-caller` | Multi-provider router (`multi_provider`) | Provider failover |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Passing work per cost selector | `model-tier-chooser:tier_selector` | [hubofhubs/the_world/model_plumbing/model_tier_chooser/tiers.py](model_tier_chooser/tiers.py) |  |
| Anthropic provider | `vendor-model-caller:anthropic` | [hubofhubs/the_world/model_plumbing/vendor_model_caller/anthropic.py](vendor_model_caller/anthropic.py) |  |
| DeepSeek provider | `vendor-model-caller:deepseek` | [hubofhubs/the_world/model_plumbing/vendor_model_caller/openai.py](vendor_model_caller/openai.py) |  |
| Gemini provider | `vendor-model-caller:gemini` | [hubofhubs/the_world/model_plumbing/vendor_model_caller/gemini.py](vendor_model_caller/gemini.py) |  |
| Multi-provider router | `vendor-model-caller:multi_provider` | [hubofhubs/the_world/model_plumbing/vendor_model_caller/router.py](vendor_model_caller/router.py) |  |
| OpenAI provider | `vendor-model-caller:openai` | [hubofhubs/the_world/model_plumbing/vendor_model_caller/openai.py](vendor_model_caller/openai.py) |  |
| Claude Code CLI | `vendor-model-caller:claude_cli` | [hubofhubs/the_world/model_plumbing/vendor_model_caller/claude_cli.py](vendor_model_caller/claude_cli.py) |  |

### Metrics

- Tier choice by passing work per cost (`metric-model-tier-chooser`): `esoi run reason_and_answer --impl tier_selector`
- Tier passing work per cost (`metric-tier-passing-work-per-cost`): `python3 -m pytest hubofhubs/the_world/tests/test_tiers.py`
- Model quality on hard maths (`metric-model-quality`): `esoi run model_quality_aime --impl claude_haiku; esoi run model_quality_aime --impl claude_sonnet; esoi run model_quality_aime --impl claude_opus; esoi run model_quality_aime --impl gemini_2_5_flash_lite; esoi run model_quality_aime --impl gemini_2_5_flash; esoi run model_quality_aime --impl gpt_5_nano; esoi run model_quality_aime --impl gpt_5_mini; esoi run model_quality_aime --impl deepseek_flash`
- Vendor arms answer (`metric-vendor-answers`): `esoi run call_a_model --impl gemini; esoi run call_a_model --impl openai; esoi run call_a_model --impl deepseek; esoi run call_a_model --impl claude_cli`
- Provider failover (`metric-vendor-model-caller`): `esoi run provider_failover --impl multi_provider`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
