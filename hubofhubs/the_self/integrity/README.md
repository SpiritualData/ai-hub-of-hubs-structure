# Integrity

**Purpose:** Keep the whole honest and usable by any consumer: what the system says about itself and what it did matches the record.

Breadcrumb: [Top](../../../esoi/README.md) > [The parts working as one whole](../README.md) > Integrity

Part of [The parts working as one whole](../README.md)

## Integrity (`system-integrity`)

- Out of scope: Judging whether an answer to a person is good (Response Quality does that), fixing what it finds, and choosing which arm is best.
- Delegates to: the-assembler
- Entry call: `hubofhubs.run("system-integrity", ['examplevendor'])`
- Selected implementation: Audit of vendor wording, staleness and configuration (`prompts_as_data`)
- Metric: Consumer-specific strings found by scan, Intents whose solutions one paragraph and one diagram explain as the code builds them
- Implemented by: [`hubofhubs/the_self/__init__.py`](../__init__.py), [`hubofhubs/the_self/assembler/__init__.py`](../assembler/__init__.py), [`hubofhubs/the_self/assembler/arm_needs.py`](../assembler/arm_needs.py), [`hubofhubs/the_self/assembler/cli.py`](../assembler/cli.py), [`hubofhubs/the_self/assembler/interface.py`](../assembler/interface.py), [`hubofhubs/the_self/assembler/oneline.py`](../assembler/oneline.py), [`hubofhubs/the_self/assembler/resolution.py`](../assembler/resolution.py), [`hubofhubs/the_self/assembler/tests/test_safe_loading.py`](../assembler/tests/test_safe_loading.py) and 22 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Audit of vendor wording, staleness and configuration | `system-integrity:prompts_as_data` | Scans the hub for vendor-name branches and reports how stale its research is and how much of it connects by configuration. | [`hubofhubs/the_self/integrity/audit.py`](audit.py) | selected |

## Metrics

- Consumer-specific strings found by scan (`metric-system-integrity`)
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`)

## Problems

- One product leaks into shared code (`HP6`): One product's prompts and settings creep into shared code, so others have to find and strip them out before they can reuse it.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The parts working as one whole](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
