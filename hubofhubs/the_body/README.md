# The form and internal context of a system

**Vision statement:** The AI system fits the particular system it lives in.

Breadcrumb: [Top](../../esoi/README.md) > The form and internal context of a system

This sub-intent arises as the implementation `the-body:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: A system's own data and the integrations it already runs change for reasons of their own, apart from the outside world and from model accuracy. If a system can declare its own sources instead of having parts rewritten for it, any product can adopt the hub.

## How the solutions fit together

Body is the form of the system and the context that belongs to it, and it lets anyone apply the hub to their own system by declaring where the data lives, where requests come from and which enduring integrations the AI may use. Internal Context declares where the system's data lives, whether each source belongs to the system or to a person, and which outside tool reads it, keeps what the system knows in Card Store and keeps the run record. Intake Sources declares where the requests come from. Hands makes sure that the system's own AI tool registry, LLM platform and guardrails are accessible to the AI and used by it.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Internal Context<br/><i>internal-context</i>"]
    s1["Card Store<br/><i>card-store</i>"]
    s1 -->|"The id of an added card, a card or nothing for an id, the cards matching a query or a tag, whether a delete removed one, and the count"| s0
```

## One level below

This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.

- Hands (solution with no page of its own, its implementations are in this intent's records): Make the integrations a system already depends on accessible to the AI and actually used.
- [Intake Sources](intake_sources/README.md) (solution with implementations): Let a system say where its requests come from and read them, without the hub being written for that system.
- [Internal Context](internal_context/README.md) (solution with implementations and parts below it): Let the AI know what a particular system knows, without the hub being written for that system: the declaration of where its data lives and whether each source belongs to the system or to a person, the configuration its tools need, and the run record the flow writes.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Hands | `the-hands` | `hubofhubs.run("the-hands", '')` | none selected | Declared integrations are reachable and used |
| Intake Sources | `intake-sources` | `hubofhubs.run("intake-sources", {'source': '', 'limit': 10})` | Folder of queued requests (`folder_queue`) | Requests read from a declared source, once |
| Internal Context | `internal-context` | `hubofhubs.run("internal-context", 'rust release')` | Declared sources, cards kept and built from files (`composition`) | An internal source reaches the AI through one declaration |
| Card Store | `card-store` | `hubofhubs.run("card-store", 'rust release')` | Local card store (`local_card_store`) | Cards found again, none lost |

## Problems and ideals

**Problems**

- Picks go out of date (`HP3`): A part that was best a few months ago can be overtaken by a newer one, and without a fresh comparison the team using it often does not notice.
- App connections rebuilt by every product (`HP7`): Many products rebuild each app connection (calendar, drive, notes, chat) with their own screen, storage and tool code, so a new app costs code in every layer and often arrives months after hubs list it.
- One integration needs several hubs (`hprob-one-integration-needs-several-hubs`): An app connection (a calendar, a drive, a chat) is often served better by several hubs combined than by any one, but a product usually wires a single hub and hand-writes the rest.
- System context not declared (`hprob-system-context-not-declared`): A system's own knowledge, in its internal APIs, databases and local files, cannot be offered to the AI without code written for that system.
- Enduring integrations unused (`hprob-enduring-integrations-unused`): A system often already has enduring integrations, such as its own AI tool registry, LLM platform and guardrails, and the AI cannot reach them or does not use them.

**Ideals**

- Common-sense metrics, sourced stages (`hideal-common-sense-metrics-with-sourced-stages`): Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- Best in each circumstance, with variants (`hideal-best-in-circumstance-with-variants`): Each user gets the part that is best under their own limits, such as cost, speed, language or input size.
- Guards earn their place (`hideal-guards-earn-their-place`): A guard is kept only when it catches something the model or harness would miss.
- Agent work at the lowest cost that does it well (`hideal-cheap-fast-harness-with-ideal-context`): Work handed to an agent finishes at the lowest cost and time that keeps the same quality, with context that is enough and no more.
- Every connected app fully usable (`hideal-hubs-combined-per-integration`): Each app a user connects offers everything the AI may do with it, and a new app needs no new code.
- Proportionate, current cards (`hideal-cards-proportionate-and-current`): A folder's cards cover what is in it, about one card per thing people ask about, and change when the files change.
- A system offers its own context (`hideal-a-system-offers-its-own-context`): The AI can draw on everything a system knows, in any system, without code written for that system.
- Enduring integrations reach the AI (`hideal-enduring-integrations-reach-the-ai`): The integrations a system already governs are accessible to the AI and used by it.

## Metrics and their leaders

- Declared integrations are reachable and used (`metric-hands-integrations-used`)
- Requests read from a declared source, once (`metric-intake-sources`)
- An internal source reaches the AI through one declaration (`metric-internal-context`)
- Cards found again, none lost (`metric-card-store`): leader `local_card_store`, 35 of 35 cases

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records beside the code: [hubofhubs/the_body/intake_sources](intake_sources/README.md), [hubofhubs/the_body/internal_context](internal_context/README.md), [hubofhubs/the_body/internal_context/card_store](internal_context/card_store/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [metrics.csv](metrics.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- Picks go out of date (`HP3`): A part that was best a few months ago can be overtaken by a newer one, and without a fresh comparison the team using it often does not notice.
- App connections rebuilt by every product (`HP7`): Many products rebuild each app connection (calendar, drive, notes, chat) with their own screen, storage and tool code, so a new app costs code in every layer and often arrives months after hubs list it.
- One integration needs several hubs (`hprob-one-integration-needs-several-hubs`): An app connection (a calendar, a drive, a chat) is often served better by several hubs combined than by any one, but a product usually wires a single hub and hand-writes the rest.
- System context not declared (`hprob-system-context-not-declared`): A system's own knowledge, in its internal APIs, databases and local files, cannot be offered to the AI without code written for that system.
- Enduring integrations unused (`hprob-enduring-integrations-unused`): A system often already has enduring integrations, such as its own AI tool registry, LLM platform and guardrails, and the AI cannot reach them or does not use them.

### Ideals

- Common-sense metrics, sourced stages (`hideal-common-sense-metrics-with-sourced-stages`): Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- Best in each circumstance, with variants (`hideal-best-in-circumstance-with-variants`): Each user gets the part that is best under their own limits, such as cost, speed, language or input size.
- Guards earn their place (`hideal-guards-earn-their-place`): A guard is kept only when it catches something the model or harness would miss.
- Agent work at the lowest cost that does it well (`hideal-cheap-fast-harness-with-ideal-context`): Work handed to an agent finishes at the lowest cost and time that keeps the same quality, with context that is enough and no more.
- Every connected app fully usable (`hideal-hubs-combined-per-integration`): Each app a user connects offers everything the AI may do with it, and a new app needs no new code.
- Proportionate, current cards (`hideal-cards-proportionate-and-current`): A folder's cards cover what is in it, about one card per thing people ask about, and change when the files change.
- A system offers its own context (`hideal-a-system-offers-its-own-context`): The AI can draw on everything a system knows, in any system, without code written for that system.
- Enduring integrations reach the AI (`hideal-enduring-integrations-reach-the-ai`): The integrations a system already governs are accessible to the AI and used by it.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Hands | `the-hands` | none selected | Declared integrations are reachable and used |
| Intake Sources | `intake-sources` | Folder of queued requests (`folder_queue`) | Requests read from a declared source, once |
| Internal Context | `internal-context` | Declared sources, cards kept and built from files (`composition`) | An internal source reaches the AI through one declaration |
| Card Store | `card-store` | Local card store (`local_card_store`) | Cards found again, none lost |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Folder of queued requests | `intake-sources:folder_queue` | [hubofhubs/the_body/intake_sources/queue.py](intake_sources/queue.py) |  |
| Declared sources, cards kept and built from files | `internal-context:composition` | [hubofhubs/the_body/internal_context/flow.py](internal_context/flow.py) |  |
| Local card store | `card-store:local_card_store` | [hubofhubs/the_body/internal_context/card_store/cardstore.py](internal_context/card_store/cardstore.py) |  |

### Metrics

- Declared integrations are reachable and used (`metric-hands-integrations-used`): `none`
- Requests read from a declared source, once (`metric-intake-sources`): `python3 -m pytest tests/test_intake.py`
- An internal source reaches the AI through one declaration (`metric-internal-context`): `none`
- Cards found again, none lost (`metric-card-store`): `esoi run card_store --impl local_card_store`


*Generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*
