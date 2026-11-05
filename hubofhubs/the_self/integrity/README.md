# Integrity

*ESOI records kept beside the code in `hubofhubs/the_self/integrity`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The parts of the system work as one whole: each part knows its role, what the system claims matches its evidence, its records match its code, and one call builds the parts from configuration.

These are the solutions of [The parts working as one whole](../README.md).

## How the solutions fit together

The Self keeps the parts of the system working as one whole. To respond to a request, The Self asks Consciousness for the person's authority and priorities. The Self asks Body where the system's data lives. The Self passes the request on to Intelligence. The Self asks Role Understanding what that part is for, so that no part does another's work. Integrity then audits what the system says about itself and what it did against the run record, and checks that the hub stays generic, with claims that match evidence and records that match code. The Assembler builds the whole from configuration in one call and reports which seats are built and what the rest need. When asked for its health, The Self asks World how current the research is.

## Integrity (`system-integrity`)

Keep the whole honest and usable by any consumer: what the system says about itself and what it did matches the record.

- Entry call: `hubofhubs.run("system-integrity", ['examplevendor'])`
- Selected implementation: Audit of vendor wording, staleness and configuration (`prompts_as_data`)
- Metric: Consumer-specific strings found by scan, Intents whose solutions one paragraph and one diagram explain as the code builds them
- Implemented by: [`hubofhubs/the_self/__init__.py`](../__init__.py), [`hubofhubs/the_self/assembler/__init__.py`](../assembler/__init__.py), [`hubofhubs/the_self/assembler/arm_needs.py`](../assembler/arm_needs.py), [`hubofhubs/the_self/assembler/cli.py`](../assembler/cli.py), [`hubofhubs/the_self/assembler/interface.py`](../assembler/interface.py), [`hubofhubs/the_self/assembler/oneline.py`](../assembler/oneline.py), [`hubofhubs/the_self/assembler/resolution.py`](../assembler/resolution.py), [`hubofhubs/the_self/assembler/zero_config.py`](../assembler/zero_config.py) and 20 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Audit of vendor wording, staleness and configuration | `system-integrity:prompts_as_data` | [`hubofhubs/the_self/integrity/audit.py`](audit.py) | selected |

## Metrics

- Consumer-specific strings found by scan (`metric-system-integrity`)
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`)

## Problems

- One product leaks into shared code (`HP6`): One product's prompts and settings leak into shared code, so it cannot be reused by anyone else.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The parts working as one whole](../README.md)
- Repository: [top README](../../../README.md)
