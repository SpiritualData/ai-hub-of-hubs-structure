# Model Tier Chooser

**Purpose:** Pick, for each model tier, the model that does the most passing work per cost.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Asking a model through one measured path](../README.md) > Model Tier Chooser

Part of [Asking a model through one measured path](../README.md)

## Model Tier Chooser (`model-tier-chooser`)

- Out of scope: Calling the model (the Vendor Model Caller does that) and the wording of the question (each part does that).
- Delegates to: vendor-model-caller
- Entry call: `hubofhubs.run("model-tier-chooser", {'available': ['anthropic']})`
- Selected implementation: Passing work per cost selector (`tier_selector`)
- Metric: Tier choice by passing work per cost, Tier passing work per cost, Model quality on hard maths, Vendor arms answer
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 133 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Passing work per cost selector | `model-tier-chooser:tier_selector` | Ranks each provider and model by passing work per dollar on shared cases at the prices on file, counting prepaid credits as cost. | [`hubofhubs/the_world/model_plumbing/model_tier_chooser/tiers.py`](tiers.py) | selected |

## Metrics

- Tier choice by passing work per cost (`metric-model-tier-chooser`): leader `tier_selector`, 36 of 36 cases
- Tier passing work per cost (`metric-tier-passing-work-per-cost`)
- Model quality on hard maths (`metric-model-quality`): leader `deepseek_v4_pro`, 3 of 3 cases
- Vendor arms answer (`metric-vendor-answers`): leader `claude_cli`, 3 of 3 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Asking a model through one measured path](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
