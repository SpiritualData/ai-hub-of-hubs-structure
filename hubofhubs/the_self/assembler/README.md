# Assembler

*ESOI records kept beside the code in `hubofhubs/the_self/assembler`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The parts of the system work as one whole: each part knows its role, what the system claims matches its evidence, its records match its code, and one call builds the parts from configuration.

These are the solutions of [The parts working as one whole](../README.md).

## How the solutions fit together

The Self keeps the parts of the system working as one whole through the Assembler and Integrity. The Assembler builds the whole from configuration in one call and reports which seats are built and what the rest need. Integrity audits what the system says about itself and what it did, including the run record, and checks that the hub stays generic, with claims that match evidence and records that match code. Role Understanding states what each part is for, so that no part does another's work.

## Assembler (`the-assembler`)

Build the whole from the best-measured arm of every seat and report its coverage, with no glue written by the consumer.

- Entry call: `hubofhubs.run("the-assembler", {})`
- Selected implementation: One-call assembly of the whole hub (`zero_config`)
- Metric: Whole assembly
- Implemented by: [`.env.example`](../../../.env.example), [`.gitignore`](../../../.gitignore), [`CHANGELOG.md`](../../../CHANGELOG.md), [`CLAUDE.md`](../../../CLAUDE.md), [`CONTRIBUTING.md`](../../../CONTRIBUTING.md), [`LICENSE`](../../../LICENSE), [`NOTICE`](../../../NOTICE), [`esoi.toml`](../../../esoi.toml) and 230 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| One-call assembly of the whole hub | `the-assembler:zero_config` | [`hubofhubs/the_self/assembler/zero_config.py`](zero_config.py) | selected |

## Metrics

- Whole assembly (`metric-the-assembler`)

## Problems

- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is judged part by part, so nobody checks that it behaves like one capable assistant from where the user sits: asked for something real, it should know what it may do, ask before anything irreversible and say truthfully what it did.

## Ideals

- Capable from the user's seat (`hideal-capable-from-the-users-seat`): The assembled hub is judged as the user meets it: one capable assistant that gets real work done, asks before it does anything that cannot be undone, and reports only what it did.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The parts working as one whole](../README.md)
- Repository: [top README](../../../README.md)
