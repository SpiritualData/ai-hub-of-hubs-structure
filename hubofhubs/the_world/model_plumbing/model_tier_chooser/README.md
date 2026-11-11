# Model Tier Chooser

**Purpose:** Pick, for each model tier, the model that best fits what the tier is for, by that tier's own metric.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Asking a model through one measured path](../README.md) > Model Tier Chooser

Part of [Asking a model through one measured path](../README.md)

## Model Tier Chooser (`model-tier-chooser`)

- Out of scope: Calling the model (the Vendor Model Caller does that) and the wording of the question (each part does that).
- Delegates to: vendor-model-caller
- Entry call: `hubofhubs.run("model-tier-chooser", {'available': ['anthropic']})`
- Selected implementation: Tier metric selector (`tier_selector`)
- Metric: Tier default by the tier's own public metric, Fast tier default, Balanced tier default, Quality tier default, Best tier default, Tier passing work per cost, Model quality on hard maths, Vendor arms answer
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/investigation_record.py`](../../learning/investigation_record.py), [`hubofhubs/the_world/learning/investigation_store.py`](../../learning/investigation_store.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py) and 189 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Tier metric selector | `model-tier-chooser:tier_selector` | Keeps the arms at least as good as the tier's held default on public evaluations (anchored minimums) and picks the cheapest and fastest of them by list price and published speed (public_metric.py); passing work per dollar on shared cases stays available as select and pick over measured arms. | [`hubofhubs/the_world/model_plumbing/model_tier_chooser/tiers.py`](tiers.py) | selected |

## Metrics

- Tier default by the tier's own public metric (`metric-model-tier-chooser`): leader `tier_selector`, 36 of 36 cases
- Tier passing work per cost (`metric-tier-passing-work-per-cost`)
- Model quality on hard maths (`metric-model-quality`): leader `deepseek_v4_pro`, 3 of 3 cases
- Vendor arms answer (`metric-vendor-answers`): leader `claude_cli`, 3 of 3 cases
- Fast tier default (`metric-tier-fast`)
- Balanced tier default (`metric-tier-balanced`)
- Quality tier default (`metric-tier-quality`)
- Best tier default (`metric-tier-best`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Asking a model through one measured path](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
