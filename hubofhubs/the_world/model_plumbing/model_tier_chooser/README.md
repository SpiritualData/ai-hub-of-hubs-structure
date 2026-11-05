# Model Tier Chooser

*ESOI records kept beside the code in `hubofhubs/the_world/model_plumbing/model_tier_chooser`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

Every part asks a model through one path: the tier is chosen by measurement and the vendor behind it can change without any part noticing.

These are the solutions of [Asking a model through one measured path](../README.md).

## How the solutions fit together

Model Plumbing is how every part asks a model. Model Tier Chooser picks, per tier, the model that did the most passing work per unit of cost. Vendor Model Caller asks that vendor and steps to the next provider when one fails.

## Model Tier Chooser (`model-tier-chooser`)

Pick, for each model tier, the model that does the most passing work per cost.

- Entry call: `hubofhubs.run("model-tier-chooser", {'available': ['anthropic']})`
- Selected implementation: Passing work per cost selector (`tier_selector`)
- Metric: Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 122 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Passing work per cost selector | `model-tier-chooser:tier_selector` | [`hubofhubs/the_world/model_plumbing/model_tier_chooser/tiers.py`](tiers.py) | selected |

## Metrics

- Tier choice by passing work per cost (`metric-model-tier-chooser`): leader `tier_selector`, 36 of 36 cases
- Tier passing work per cost (`metric-tier-passing-work-per-cost`)
- Model quality on hard maths (`metric-model-quality`): leader `deepseek_v4_pro`, 3 of 3 cases
- Vendor arms answer (`metric-vendor-answers`): leader `claude_cli`, 3 of 3 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Asking a model through one measured path](../README.md)
- Repository: [top README](../../../../README.md)
