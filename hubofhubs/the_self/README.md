# The parts working as one whole

**Vision statement:** The parts of the AI system work together as one whole.

Breadcrumb: [Top](../../esoi/README.md) > The parts working as one whole

This sub-intent arises as the implementation `the-self:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: An assembled system that checks itself, and parts that each state what they are for, are things a whole needs and rarely gets from its parts alone. Whoever builds on the hub gets them without writing the glue.

## How the solutions fit together

The Self keeps the parts of the system working as one whole. To respond to a request, The Self asks Consciousness for the person's authority and priorities. The Self asks Body where the system's data lives. The Self passes the request on to Intelligence. The Self asks Role Understanding what that part is for, so that no part does another's work. Integrity then audits what the system says about itself and what it did against the run record, and checks that the hub stays generic, with claims that match evidence and records that match code. The Assembler builds the whole from configuration in one call and reports which seats are built and what the rest need. When asked for its health, The Self asks World how current the research is.

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- [Assembler](assembler/README.md) (solution with implementations): Build the whole from the best-measured arm of every seat and report its coverage, with no glue written by the consumer.
- [Integrity](integrity/README.md) (solution with implementations): Keep the whole honest and usable by any consumer: what the system says about itself and what it did matches the record.
- [Role Understanding](role_understanding/README.md) (solution with implementations): Give every part a role in the whole that the part and the Assembler can both read.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Assembler | `the-assembler` | `hubofhubs.run("the-assembler", {})` | One-call assembly of the whole hub (`zero_config`) | Whole assembly |
| Integrity | `system-integrity` | `hubofhubs.run("system-integrity", ['examplevendor'])` | Audit of vendor wording, staleness and configuration (`prompts_as_data`) | Consumer-specific strings found by scan, Intents whose solutions one paragraph and one diagram explain as the code builds them |
| Role Understanding | `role-understanding` | `hubofhubs.run("role-understanding", 'the-assembler')` | Role checked against the part's calls (`checked_role`) | Roles stated as recorded and contradictions found |

## Problems and ideals

**Problems**

- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is mostly measured part by part, and whole-system checks are usually hand-run demos, so few teams have a repeatable, recorded way to see whether it behaves as one capable assistant: knowing what it may do, asking before anything irreversible and saying truthfully what it did.
- One product leaks into shared code (`HP6`): One product's prompts and settings creep into shared code, so others have to find and strip them out before they can reuse it.
- Parts forget their role (`hprob-parts-forget-their-role`): Parts assembled together drift: one does another part's work, hides its own failure or claims more than its evidence shows, and no part is responsible for the coherence of the whole.

**Ideals**

- Capable from the user's seat (`hideal-capable-from-the-users-seat`): Used as a whole, the hub is one capable assistant that gets real work done, asks before anything that cannot be undone, and reports only what it did.
- Every part knows its role (`hideal-every-part-knows-its-role`): Each part knows what it is for, what it hands on and what it leaves to the others.

## Metrics and their leaders

- Whole assembly (`metric-the-assembler`)
- Consumer-specific strings found by scan (`metric-system-integrity`)
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`)
- Roles stated as recorded and contradictions found (`metric-role-understanding`): leader `checked_role`, 13 of 13 cases

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records beside the code: [hubofhubs/the_self/assembler](assembler/README.md), [hubofhubs/the_self/integrity](integrity/README.md), [hubofhubs/the_self/role_understanding](role_understanding/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is mostly measured part by part, and whole-system checks are usually hand-run demos, so few teams have a repeatable, recorded way to see whether it behaves as one capable assistant: knowing what it may do, asking before anything irreversible and saying truthfully what it did.
- One product leaks into shared code (`HP6`): One product's prompts and settings creep into shared code, so others have to find and strip them out before they can reuse it.
- Parts forget their role (`hprob-parts-forget-their-role`): Parts assembled together drift: one does another part's work, hides its own failure or claims more than its evidence shows, and no part is responsible for the coherence of the whole.

### Ideals

- Capable from the user's seat (`hideal-capable-from-the-users-seat`): Used as a whole, the hub is one capable assistant that gets real work done, asks before anything that cannot be undone, and reports only what it did.
- Every part knows its role (`hideal-every-part-knows-its-role`): Each part knows what it is for, what it hands on and what it leaves to the others.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Assembler | `the-assembler` | One-call assembly of the whole hub (`zero_config`) | Whole assembly |
| Integrity | `system-integrity` | Audit of vendor wording, staleness and configuration (`prompts_as_data`) | Consumer-specific strings found by scan, Intents whose solutions one paragraph and one diagram explain as the code builds them |
| Role Understanding | `role-understanding` | Role checked against the part's calls (`checked_role`) | Roles stated as recorded and contradictions found |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| One-call assembly of the whole hub | `the-assembler:zero_config` | [hubofhubs/the_self/assembler/zero_config.py](assembler/zero_config.py) |  |
| Audit of vendor wording, staleness and configuration | `system-integrity:prompts_as_data` | [hubofhubs/the_self/integrity/audit.py](integrity/audit.py) |  |
| Role as the record states it | `role-understanding:recorded_role` | [hubofhubs/the_self/role_understanding/roles.py](role_understanding/roles.py) |  |
| Role checked against the part's calls | `role-understanding:checked_role` | [hubofhubs/the_self/role_understanding/roles.py](role_understanding/roles.py) |  |

### Metrics

- Whole assembly (`metric-the-assembler`): `none`
- Consumer-specific strings found by scan (`metric-system-integrity`): `none`
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`): `python3 -m esoi.structure.structure_check.coherence --gate`
- Roles stated as recorded and contradictions found (`metric-role-understanding`): `esoi run role_understanding --impl recorded_role; esoi run role_understanding --impl checked_role`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
