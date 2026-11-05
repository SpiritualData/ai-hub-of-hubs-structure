# The form and internal context of a system

The AI system has a form and its own internal context, and the hub applies to a particular system by providing adapters or declaring the system's internal APIs, databases and files.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `the-body:composition` of its parent intent [`hub-of-hubs`](../../esoi/README.md). Opportunities: A system's own data, and the integrations it already governs, are a different kind of evolution from the one the parent solution measures. Declaring a system's own sources, rather than rewriting parts for it, lets any product adopt the hub.

## How the solutions fit together

Body is the form of the system and the context that belongs to it, and it lets anyone apply the hub to their own system by declaring where the data lives, where requests come from and which enduring integrations the AI may use. Internal Context declares where the system's data lives, whether each source belongs to the system or to a person, and which outside tool reads it, keeps what the system knows in Card Store and keeps the run record. Intake Sources declares where the requests come from. Hands makes sure that the system's own AI tool registry, LLM platform and guardrails are accessible to the AI and used by it.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Card Store<br/><i>card-store</i>"]
    s1["Internal Context<br/><i>internal-context</i>"]
    s0 -->|"The id of an added card, a card or nothing for an id, the..."| s1
```

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Hands | `the-hands` | `hubofhubs.run("the-hands", '')` | none selected | Integration added with zero code, Integration served by combined hubs, Integration available within the weekly refresh, Integration credentials stay with their user, Share of connections that need no code, Share of connections that need no code |
| Card Store | `card-store` | `hubofhubs.run("card-store", 'rust release')` | Local card store (`local_card_store`) | Cards found again, none lost |
| Internal Context | `internal-context` | `hubofhubs.run("internal-context", 'rust release')` | Declared sources, cards kept and built from files (`composition`) | An internal source reaches the AI through one declaration |
| Intake Sources | `intake-sources` | `hubofhubs.run("intake-sources", {'source': '', 'limit': 10})` | Folder of queued requests (`folder_queue`) | Requests read from a declared source, once |

## Problems and ideals

**Problems**

- Stale picks (`HP3`): Hubs go stale.
- App connections rebuilt by every product (`HP7`): Every product re-builds each app connection (calendar, drive, notes, chat) with its own screen, storage and tool code, so a new app costs code in every layer and arrives months after hubs list it.
- One integration needs several hubs (`hprob-one-integration-needs-several-hubs`): One app connection (a calendar, a drive, a chat) is served better by several hubs combined than by any one, but a product wires a single hub and hand-writes the rest.
- System context not declared (`hprob-system-context-not-declared`): A system's own knowledge, in its internal APIs, databases and local files, cannot be offered to the AI without code written for that system.
- Enduring integrations unused (`hprob-enduring-integrations-unused`): A system already has enduring integrations, such as its own AI tool registry, LLM platform and guardrails, and the AI cannot reach them or does not use them.

**Ideals**

- Common-sense metrics, sourced stages (`hideal-common-sense-metrics-with-sourced-stages`): Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- Best in each circumstance, with variants (`hideal-best-in-circumstance-with-variants`): The hub names the best part for each circumstance and not one winner, by comparing variants of a part (one setting changed) on the same cases.
- Guards earn their place (`hideal-guards-earn-their-place`): A guard is kept only when it catches something the model or harness would miss, shown by running the same cases with and without it.
- Cheap, fast harness with ideal context (`hideal-cheap-fast-harness-with-ideal-context`): An agent harness is chosen for the lowest cost and time at the same pass rate, given the best context the hub can assemble for it, and the choice accounts for sub-agents and recursion.
- Hubs combined per integration (`hideal-hubs-combined-per-integration`): An integration is served by the combination of hubs that covers the most of it, chosen by data and never by one hub's reach.
- Proportionate, current cards (`hideal-cards-proportionate-and-current`): A folder's cards cover what is in it, about one card per thing people ask about, and change when the files change.
- A system offers its own context (`hideal-a-system-offers-its-own-context`): A system declares its own sources once, and the hub reads them through adapters; local files work by default.
- Enduring integrations reach the AI (`hideal-enduring-integrations-reach-the-ai`): The integrations a system already governs are accessible to the AI and used by it.

## Metrics and their leaders

- Integration added with zero code (`metric-integration-added-with-zero-code`)
- Integration available within the weekly refresh (`metric-integration-availability-lag`)
- Integration credentials stay with their user (`metric-integration-credential-isolation`)
- Cards found again, none lost (`metric-card-store`): leader `local_card_store`, 35 of 35 cases
- Integration served by combined hubs (`metric-integration-served-by-combined-hubs`)
- An internal source reaches the AI through one declaration (`metric-internal-context`)
- Requests read from a declared source, once (`metric-intake-sources`)

## Where to go next

- Parent intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- Stale picks (`HP3`): Hubs go stale.
- App connections rebuilt by every product (`HP7`): Every product re-builds each app connection (calendar, drive, notes, chat) with its own screen, storage and tool code, so a new app costs code in every layer and arrives months after hubs list it.
- One integration needs several hubs (`hprob-one-integration-needs-several-hubs`): One app connection (a calendar, a drive, a chat) is served better by several hubs combined than by any one, but a product wires a single hub and hand-writes the rest.
- System context not declared (`hprob-system-context-not-declared`): A system's own knowledge, in its internal APIs, databases and local files, cannot be offered to the AI without code written for that system.
- Enduring integrations unused (`hprob-enduring-integrations-unused`): A system already has enduring integrations, such as its own AI tool registry, LLM platform and guardrails, and the AI cannot reach them or does not use them.

### Ideals

- Common-sense metrics, sourced stages (`hideal-common-sense-metrics-with-sourced-stages`): Every metric is a plain check anyone would accept, and its stages come from public evaluations whose sources are named and compared with each other.
- Best in each circumstance, with variants (`hideal-best-in-circumstance-with-variants`): The hub names the best part for each circumstance and not one winner, by comparing variants of a part (one setting changed) on the same cases.
- Guards earn their place (`hideal-guards-earn-their-place`): A guard is kept only when it catches something the model or harness would miss, shown by running the same cases with and without it.
- Cheap, fast harness with ideal context (`hideal-cheap-fast-harness-with-ideal-context`): An agent harness is chosen for the lowest cost and time at the same pass rate, given the best context the hub can assemble for it, and the choice accounts for sub-agents and recursion.
- Hubs combined per integration (`hideal-hubs-combined-per-integration`): An integration is served by the combination of hubs that covers the most of it, chosen by data and never by one hub's reach.
- Proportionate, current cards (`hideal-cards-proportionate-and-current`): A folder's cards cover what is in it, about one card per thing people ask about, and change when the files change.
- A system offers its own context (`hideal-a-system-offers-its-own-context`): A system declares its own sources once, and the hub reads them through adapters; local files work by default.
- Enduring integrations reach the AI (`hideal-enduring-integrations-reach-the-ai`): The integrations a system already governs are accessible to the AI and used by it.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Hands | `the-hands` | none selected | Integration added with zero code, Integration served by combined hubs, Integration available within the weekly refresh, Integration credentials stay with their user, Share of connections that need no code, Share of connections that need no code |
| Card Store | `card-store` | Local card store (`local_card_store`) | Cards found again, none lost |
| Internal Context | `internal-context` | Declared sources, cards kept and built from files (`composition`) | An internal source reaches the AI through one declaration |
| Intake Sources | `intake-sources` | Folder of queued requests (`folder_queue`) | Requests read from a declared source, once |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Local card store | `card-store:local_card_store` | [hubofhubs/cardstore.py](../cardstore.py) |  |
| Declared sources, cards kept and built from files | `internal-context:composition` | [hubofhubs/flows.py](../flows.py) |  |
| Folder of queued requests | `intake-sources:folder_queue` | [hubofhubs/intake/queue.py](../intake/queue.py) |  |

### Metrics

- Integration added with zero code (`metric-integration-added-with-zero-code`): `none`
- Integration available within the weekly refresh (`metric-integration-availability-lag`): `none`
- Integration credentials stay with their user (`metric-integration-credential-isolation`): `none`
- Cards found again, none lost (`metric-card-store`): `esoi run card_store --impl local_card_store`
- Integration served by combined hubs (`metric-integration-served-by-combined-hubs`): `none`
- An internal source reaches the AI through one declaration (`metric-internal-context`): `none`
- Requests read from a declared source, once (`metric-intake-sources`): `python3 -m pytest tests/test_intake.py`
