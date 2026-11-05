# The parts working as one whole

The parts of the system work as one whole: each part knows its role, what the system claims matches its evidence, its records match its code, and one call builds the parts from configuration.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-self:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: A system can check itself, each part can state what it is for, and every part can share one measured way of asking a model, none of which the assembly alone asks for. Whoever builds on the hub gets the integration without writing it.

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

- Parts forget their role (`hprob-parts-forget-their-role`): Parts assembled together drift: one does another part's work, hides its own failure or claims more than its evidence shows, and nobody owns the coherence of the whole.
- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is judged part by part, so nobody checks that it behaves like one capable assistant from where the user sits: asked for something real, it should know what it may do, ask before anything irreversible and say truthfully what it did.
- One product leaks into shared code (`HP6`): One product's prompts and settings leak into shared code, so it cannot be reused by anyone else.

**Ideals**

- Every part knows its role (`hideal-every-part-knows-its-role`): Each part knows what it is for, what it hands on and what it leaves to the others.
- Capable from the user's seat (`hideal-capable-from-the-users-seat`): The assembled hub is judged as the user meets it: one capable assistant that gets real work done, asks before it does anything that cannot be undone, and reports only what it did.

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

- Parts forget their role (`hprob-parts-forget-their-role`): Parts assembled together drift: one does another part's work, hides its own failure or claims more than its evidence shows, and nobody owns the coherence of the whole.
- Assembly judged part by part (`hprob-assembly-judged-part-by-part`): An assembled system is judged part by part, so nobody checks that it behaves like one capable assistant from where the user sits: asked for something real, it should know what it may do, ask before anything irreversible and say truthfully what it did.
- One product leaks into shared code (`HP6`): One product's prompts and settings leak into shared code, so it cannot be reused by anyone else.

### Ideals

- Every part knows its role (`hideal-every-part-knows-its-role`): Each part knows what it is for, what it hands on and what it leaves to the others.
- Capable from the user's seat (`hideal-capable-from-the-users-seat`): The assembled hub is judged as the user meets it: one capable assistant that gets real work done, asks before it does anything that cannot be undone, and reports only what it did.

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
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`): `python3 -m esoi.coherence --gate`
