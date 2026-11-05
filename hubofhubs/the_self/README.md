# The parts working as one whole

The parts of the AI system work together as one whole.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-self:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: An assembled system that checks itself, and parts that each state what they are for, are things a whole needs and rarely gets from its parts alone. Whoever builds on the hub gets them without writing the glue.

## How the solutions fit together

The Self keeps the parts of the system working as one whole. To respond to a request, The Self asks Consciousness for the person's authority and priorities. The Self asks Body where the system's data lives. The Self passes the request on to Intelligence. The Self asks Role Understanding what that part is for, so that no part does another's work. Integrity then audits what the system says about itself and what it did against the run record, and checks that the hub stays generic, with claims that match evidence and records that match code. The Assembler builds the whole from configuration in one call and reports which seats are built and what the rest need. When asked for its health, The Self asks World how current the research is.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Role Understanding | `role-understanding` | `hubofhubs.run("role-understanding", 'the-assembler')` | none selected | Behaviour matches the stated role |
| Assembler | `the-assembler` | `hubofhubs.run("the-assembler", {})` | One-call assembly of the whole hub (`zero_config`) | Whole assembly |
| Integrity | `system-integrity` | `hubofhubs.run("system-integrity", ['examplevendor'])` | Audit of vendor wording, staleness and configuration (`prompts_as_data`) | Consumer-specific strings found by scan, Intents whose solutions one paragraph and one diagram explain as the code builds them |

## Problems and ideals

**Problems**

- Parts forget their role (`hprob-parts-forget-their-role`): Parts assembled together drift: one does another part's work, hides its own failure or claims more than its evidence shows, and no part is responsible for the coherence of the whole.
- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is mostly measured part by part, and whole-system checks are usually hand-run demos, so few teams have a repeatable, recorded way to see whether it behaves as one capable assistant: knowing what it may do, asking before anything irreversible and saying truthfully what it did.
- One product leaks into shared code (`HP6`): One product's prompts and settings creep into shared code, so others have to find and strip them out before they can reuse it.

**Ideals**

- Every part knows its role (`hideal-every-part-knows-its-role`): Each part knows what it is for, what it hands on and what it leaves to the others.
- Capable from the user's seat (`hideal-capable-from-the-users-seat`): Used as a whole, the hub is one capable assistant that gets real work done, asks before anything that cannot be undone, and reports only what it did.

## Metrics and their leaders

- Behaviour matches the stated role (`metric-role-understanding`)
- Whole assembly (`metric-the-assembler`)
- Consumer-specific strings found by scan (`metric-system-integrity`)
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`)

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records beside the code: [hubofhubs/the_self/assembler](assembler/README.md), [hubofhubs/the_self/integrity](integrity/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Parts forget their role (`hprob-parts-forget-their-role`): Parts assembled together drift: one does another part's work, hides its own failure or claims more than its evidence shows, and no part is responsible for the coherence of the whole.
- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is mostly measured part by part, and whole-system checks are usually hand-run demos, so few teams have a repeatable, recorded way to see whether it behaves as one capable assistant: knowing what it may do, asking before anything irreversible and saying truthfully what it did.
- One product leaks into shared code (`HP6`): One product's prompts and settings creep into shared code, so others have to find and strip them out before they can reuse it.

### Ideals

- Every part knows its role (`hideal-every-part-knows-its-role`): Each part knows what it is for, what it hands on and what it leaves to the others.
- Capable from the user's seat (`hideal-capable-from-the-users-seat`): Used as a whole, the hub is one capable assistant that gets real work done, asks before anything that cannot be undone, and reports only what it did.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Role Understanding | `role-understanding` | none selected | Behaviour matches the stated role |
| Assembler | `the-assembler` | One-call assembly of the whole hub (`zero_config`) | Whole assembly |
| Integrity | `system-integrity` | Audit of vendor wording, staleness and configuration (`prompts_as_data`) | Consumer-specific strings found by scan, Intents whose solutions one paragraph and one diagram explain as the code builds them |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| One-call assembly of the whole hub | `the-assembler:zero_config` | [hubofhubs/the_self/assembler/zero_config.py](assembler/zero_config.py) |  |
| Audit of vendor wording, staleness and configuration | `system-integrity:prompts_as_data` | [hubofhubs/the_self/integrity/audit.py](integrity/audit.py) |  |

### Metrics

- Behaviour matches the stated role (`metric-role-understanding`): `none`
- Whole assembly (`metric-the-assembler`): `none`
- Consumer-specific strings found by scan (`metric-system-integrity`): `none`
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`): `python3 -m esoi.structure.structure_check.coherence --gate`
