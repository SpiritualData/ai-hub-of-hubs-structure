# Assembler

**Purpose:** Build the whole from the best-measured arm of every seat and report its coverage, with no glue written by the consumer.

Breadcrumb: [Top](../../../esoi/README.md) > [The parts working as one whole](../README.md) > Assembler

Part of [The parts working as one whole](../README.md)

## Assembler (`the-assembler`)

- Out of scope: Running a request (The Self does that), deciding what a part does, and judging whether a response is good.
- Delegates to: role-understanding
- Entry call: `hubofhubs.run("the-assembler", {})`
- Selected implementation: One-call assembly of the whole hub (`zero_config`)
- Metric: Whole assembly
- Implemented by: [`.env.example`](../../../.env.example), [`.gitignore`](../../../.gitignore), [`CHANGELOG.md`](../../../CHANGELOG.md), [`CLAUDE.md`](../../../CLAUDE.md), [`CONTRIBUTING.md`](../../../CONTRIBUTING.md), [`LICENSE`](../../../LICENSE), [`NOTICE`](../../../NOTICE), [`conftest.py`](../../../conftest.py) and 382 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| One-call assembly of the whole hub | `the-assembler:zero_config` | Answers a question from what is remembered and from the web, holds the answer to its sources, acts on a goal only when the risk watch lets the step through, and audits the hub for consumer wording; each part comes from its selected arm. | [`hubofhubs/the_self/assembler/zero_config.py`](zero_config.py) | selected |

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

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
