# Intake Sources

**Purpose:** Let a system say where its requests come from and read them, without the hub being written for that system.

Breadcrumb: [Top](../../../esoi/README.md) > [The form and internal context of a system](../README.md) > Intake Sources

Part of [The form and internal context of a system](../README.md)

## Intake Sources (`intake-sources`)

- Out of scope: Deciding who a request is from and what to do with it (Request Intake and the flow do that) and reading or writing the system's other data (Internal Context does that).
- Delegates to: internal-context
- Entry call: `hubofhubs.run("intake-sources", {'source': '', 'limit': 10})`
- Selected implementation: Folder of queued requests (`folder_queue`)
- Metric: Requests read from a declared source, once
- Implemented by: [`hubofhubs/the_body/__init__.py`](../__init__.py), [`hubofhubs/the_body/filemodes.py`](../filemodes.py), [`hubofhubs/the_body/flow.py`](../flow.py), [`hubofhubs/the_body/hands/__init__.py`](../hands/__init__.py), [`hubofhubs/the_body/hands/interface.py`](../hands/interface.py), [`hubofhubs/the_body/intake_sources/__init__.py`](__init__.py), [`hubofhubs/the_body/intake_sources/interface.py`](interface.py), [`hubofhubs/the_body/intake_sources/queue.py`](queue.py) and 62 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Folder of queued requests | `intake-sources:folder_queue` | Requests queued as JSON files in one folder, taken oldest first and removed once taken so each is handed over once. | [`hubofhubs/the_body/intake_sources/queue.py`](queue.py) | selected |

## Metrics

- Requests read from a declared source, once (`metric-intake-sources`)

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [The form and internal context of a system](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
