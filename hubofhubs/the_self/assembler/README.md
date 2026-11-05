# Assembler

*ESOI records kept beside the code in `hubofhubs/the_self/assembler`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The parts of the AI system work together as one whole.

These are the solutions of [The parts working as one whole](../README.md).

## How the solutions fit together

The Self keeps the parts of the system working as one whole. To respond to a request, The Self asks Consciousness for the person's authority and priorities. The Self asks Body where the system's data lives. The Self passes the request on to Intelligence. The Self asks Role Understanding what that part is for, so that no part does another's work. Integrity then audits what the system says about itself and what it did against the run record, and checks that the hub stays generic, with claims that match evidence and records that match code. The Assembler builds the whole from configuration in one call and reports which seats are built and what the rest need. When asked for its health, The Self asks World how current the research is.

## Assembler (`the-assembler`)

Build the whole from the best-measured arm of every seat and report its coverage, with no glue written by the consumer.

- Entry call: `hubofhubs.run("the-assembler", {})`
- Selected implementation: One-call assembly of the whole hub (`zero_config`)
- Metric: Whole assembly
- Implemented by: [`.env.example`](../../../.env.example), [`.gitignore`](../../../.gitignore), [`CHANGELOG.md`](../../../CHANGELOG.md), [`CLAUDE.md`](../../../CLAUDE.md), [`CONTRIBUTING.md`](../../../CONTRIBUTING.md), [`LICENSE`](../../../LICENSE), [`NOTICE`](../../../NOTICE), [`conftest.py`](../../../conftest.py) and 237 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| One-call assembly of the whole hub | `the-assembler:zero_config` | [`hubofhubs/the_self/assembler/zero_config.py`](zero_config.py) | selected |

## Metrics

- Whole assembly (`metric-the-assembler`)

## Problems

- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is mostly measured part by part, and whole-system checks are usually hand-run demos, so few teams have a repeatable, recorded way to see whether it behaves as one capable assistant: knowing what it may do, asking before anything irreversible and saying truthfully what it did.

## Ideals

- Capable from the user's seat (`hideal-capable-from-the-users-seat`): Used as a whole, the hub is one capable assistant that gets real work done, asks before anything that cannot be undone, and reports only what it did.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The parts working as one whole](../README.md)
- Repository: [top README](../../../README.md)
