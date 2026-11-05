# Intake Sources

*ESOI records kept beside the code in `hubofhubs/the_body/intake_sources`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The AI system has a form and its own internal context, and the hub applies to a particular system by providing adapters or declaring the system's internal APIs, databases and files.

These are the solutions of [The form and internal context of a system](../README.md).

## How the solutions fit together

Body is the form of the system and the context that belongs to it, and it lets anyone apply the hub to their own system by declaring where the data lives, where requests come from and which enduring integrations the AI may use. Internal Context declares where the system's data lives, whether each source belongs to the system or to a person, and which outside tool reads it, keeps what the system knows in Card Store and keeps the run record. Intake Sources declares where the requests come from. Hands makes sure that the system's own AI tool registry, LLM platform and guardrails are accessible to the AI and used by it.

## Overview diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Internal Context<br/><i>internal-context</i>"]
    s1["Card Store<br/><i>card-store</i>"]
    s1 -->|"The id of an added card, a card or nothing for an id, the cards matching a query or a tag, whether a delete removed one, and the count"| s0
```

## Intake Sources (`intake-sources`)

Let a system say where its requests come from and read them, without the hub being written for that system.

- Entry call: `hubofhubs.run("intake-sources", {'source': '', 'limit': 10})`
- Selected implementation: Folder of queued requests (`folder_queue`)
- Metric: Requests read from a declared source, once
- Implemented by: [`hubofhubs/the_body/__init__.py`](../__init__.py), [`hubofhubs/the_body/filemodes.py`](../filemodes.py), [`hubofhubs/the_body/flow.py`](../flow.py), [`hubofhubs/the_body/hands/__init__.py`](../hands/__init__.py), [`hubofhubs/the_body/hands/interface.py`](../hands/interface.py), [`hubofhubs/the_body/intake_sources/__init__.py`](__init__.py), [`hubofhubs/the_body/intake_sources/interface.py`](interface.py), [`hubofhubs/the_body/intake_sources/queue.py`](queue.py) and 62 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Folder of queued requests | `intake-sources:folder_queue` | [`hubofhubs/the_body/intake_sources/queue.py`](queue.py) | selected |

## Metrics

- Requests read from a declared source, once (`metric-intake-sources`)

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The form and internal context of a system](../README.md)
- Repository: [top README](../../../README.md)
