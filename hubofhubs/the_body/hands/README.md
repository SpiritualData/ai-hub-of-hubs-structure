# Hands

**Purpose:** Make the integrations a system already depends on accessible to the AI and actually used.

Breadcrumb: [Top](../../../esoi/README.md) > [The form and internal context of a system](../README.md) > Hands

Part of [The form and internal context of a system](../README.md)

## Hands (`the-hands`)

- Out of scope: Calling a tool (Tools does that), supplying the models and guardrails (World and Model Plumbing do that), and measuring how much code a connection needs (a metric of Tools).
- Delegates to: the-tools, model-plumbing
- Entry call: `hubofhubs.run("the-hands", '')`
- Selected implementation: Declared and used (`declared_and_used`)
- Metric: Declared integrations are reachable and used
- Implemented by: [`docs/explanation/compared.md`](../../../docs/explanation/compared.md), [`docs/explanation/glossary.md`](../../../docs/explanation/glossary.md), [`docs/explanation/how-we-measure.md`](../../../docs/explanation/how-we-measure.md), [`docs/explanation/layout-of-the-hub.md`](../../../docs/explanation/layout-of-the-hub.md), [`docs/explanation/public-evidence.md`](../../../docs/explanation/public-evidence.md), [`docs/explanation/resolution-design.md`](../../../docs/explanation/resolution-design.md), [`docs/explanation/science-search.md`](../../../docs/explanation/science-search.md), [`docs/explanation/terminal-harness.md`](../../../docs/explanation/terminal-harness.md) and 51 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Declaration only | `the-hands:declaration_only` | Lists the declared integrations as the declaration gives them and checks neither reach nor use: a list a registry can print, which cannot say that a declared integration is idle or cut off. | [`hubofhubs/the_body/hands/integrations.py`](integrations.py) |  |
| Declared and used | `the-hands:declared_and_used` | Lists each declared integration of the system with ``reachable`` (it names a ``tool`` the AI can call and is not marked ``disabled``) and ``used`` (a recent run record lists it in ``used``), and marks the ones declared but never used so they are reported rather than forgotten. | [`hubofhubs/the_body/hands/integrations.py`](integrations.py) | selected |

## Metrics

- Declared integrations are reachable and used (`metric-hands-integrations-used`): leader `declared_and_used`, 8 of 8 cases

## Problems

- App connections rebuilt by every product (`HP7`): Many products rebuild each app connection (calendar, drive, notes, chat) with their own screen, storage and tool code, so a new app costs code in every layer and often arrives months after hubs list it.
- One integration needs several hubs (`hprob-one-integration-needs-several-hubs`): An app connection (a calendar, a drive, a chat) is often served better by several hubs combined than by any one, but a product usually wires a single hub and hand-writes the rest.
- Enduring integrations unused (`hprob-enduring-integrations-unused`): A system often already has enduring integrations, such as its own AI tool registry, LLM platform and guardrails, and the AI cannot reach them or does not use them.

## Ideals

- Every connected app fully usable (`hideal-hubs-combined-per-integration`): Each app a user connects offers everything the AI may do with it, and a new app needs no new code.
- Enduring integrations reach the AI (`hideal-enduring-integrations-reach-the-ai`): The integrations a system already governs are accessible to the AI and used by it.

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The form and internal context of a system](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
