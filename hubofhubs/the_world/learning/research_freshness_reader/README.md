# Research Freshness Reader

**Purpose:** Read the registry's recorded dates and report how old each area's research is.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Learning](../README.md) > Research Freshness Reader

Part of [Learning](../README.md)

## Research Freshness Reader (`research-freshness-reader`)

- Out of scope: Deciding which areas to research again (Learning does that) and doing the research.
- Entry call: `hubofhubs.run("research-freshness-reader", '2026-10-01')`
- Selected implementation: Registry date scan (`registry_scan`)
- Metric: Registry freshness reading
- Implemented by: [`docs/explanation/compared.md`](../../../../docs/explanation/compared.md), [`docs/explanation/glossary.md`](../../../../docs/explanation/glossary.md), [`docs/explanation/how-we-measure.md`](../../../../docs/explanation/how-we-measure.md), [`docs/explanation/layout-of-the-hub.md`](../../../../docs/explanation/layout-of-the-hub.md), [`docs/explanation/public-evidence.md`](../../../../docs/explanation/public-evidence.md), [`docs/explanation/resolution-design.md`](../../../../docs/explanation/resolution-design.md), [`docs/explanation/science-search.md`](../../../../docs/explanation/science-search.md), [`docs/explanation/terminal-harness.md`](../../../../docs/explanation/terminal-harness.md) and 225 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Registry date scan | `research-freshness-reader:registry_scan` | Reads the last researched date of each area in the registry and reports days since, with a 90 day staleness bar and the stale areas. | [`hubofhubs/the_world/learning/research_freshness_reader/registry.py`](registry.py) | selected |

## Metrics

- Registry freshness reading (`metric-research-freshness-reader`): leader `registry_scan`, 41 of 41 cases

## Problems

- Research dates read by hand (`hprob-research-dates-are-read-by-hand`): How old each area's research is has to be worked out by hand, so stale recommendations go unnoticed.

## Where to go next

- Up: [hubofhubs/the_world/learning](../README.md)
- Intent: [Awareness of the outside and interaction with it](../../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
