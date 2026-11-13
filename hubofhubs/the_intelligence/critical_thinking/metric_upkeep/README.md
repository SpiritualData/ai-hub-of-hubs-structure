# Metric Upkeep

**Purpose:** Keep every milestone measurable by the AI's own work, so a turn asked to make progress never has the excuse of waiting on a person.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Holding a request to a measure](../README.md) > Metric Upkeep

Part of [Holding a request to a measure](../README.md)

## Metric Upkeep (`metric-upkeep`)

- Out of scope: Choosing a request's metric (Metric Translation does that), writing the records (ESOI Application does that), checking a decision (Decision Check does that) and doing the work the metric counts (the consumer's work step does that).
- Delegates to: esoi-application, decision-check
- Entry call: `hubofhubs.run("metric-upkeep", ...)`
- Selected implementation: Record fields (`record_fields`)
- Metric: Metric states and intermediates are right
- Implemented by: [`hubofhubs/the_intelligence/critical_thinking/metric_upkeep/upkeep.py`](upkeep.py)

### Top implementations of Metric Upkeep

No implementation has a recorded result yet, so the choice is not backed by a measurement.

**How it is scored:** Metric states and intermediates are right. A metric's state matches what its fields say, a reading is recorded once, and an intermediate metric is added once, only when the check agrees it tracks the parent's done test.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Record fields | `metric-upkeep:record_fields` | Decides each metric's state from its record fields by code, reads a stale or unmeasured metric through the reader its source names, and adds one intermediate metric for a milestone whose metric moves only through a person, written through ESOI Application after Decision Check agrees the child tracks the parent's done test. | [`hubofhubs/the_intelligence/critical_thinking/metric_upkeep/upkeep.py`](upkeep.py) | selected |

## Metrics

- Metric states and intermediates are right (`metric-metric-upkeep`)

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Holding a request to a measure](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
