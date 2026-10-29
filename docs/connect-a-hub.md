# Connect a hub, do not re-wire its services

A hub gives a consumer a **class** of things through one connection: every tool an MCP server exposes, every engine SearXNG
federates, every model an OpenAI-compatible gateway routes, every app an integration aggregator exposes. One connection counts
once. A single named service (Notion, Drive, a chat tool, one search vendor, one model vendor) is an **integration**, not a
capability. Writing one by hand while a hub already covers it is recorded in `hub_integrations.csv` and is a violation unless a
reason is written beside it (for example a hosted fallback kept for outage resilience). The apps a consumer reaches grow when
the hub grows, not when the consumer gains code.

## Connections by configuration

- **Tools and data sources (MCP).** One `[[mcp_servers]]` table in the consumer's lane file. Prefer one aggregator over one
  entry per app. `hubofhubs/examples/lane-world-hub.toml` is the shape: a placeholder URL, and `token_env` naming the
  environment variable that holds the bearer token (the token never sits in a file).
- **Agents.** Any agent that speaks the Agent Client Protocol can do the deep work when the consumer is told its command.
- **Models.** Any OpenAI-compatible gateway (LiteLLM, vLLM, Ollama): a base URL, and the model-id prefixes it serves.
- **Search.** The hub for search is a federating engine such as SearXNG. A hosted JSON search API can be described as data
  (see [search-api-entries.md](search-api-entries.md)); that is a convenience for one service, not a hub connection, so it does
  not count as a capability.

## The registry files (`hubofhubs/registry/`)

| File | One row is | Columns |
|---|---|---|
| `hubs.csv` | an area (a family of hubs) | area, seat, serves, status, current_hubs, candidate_hubs, connect, last_researched, researched_by, finding_id, recommendation |
| `hub_findings.csv` | a researched candidate | finding_id, area, candidate, url, license, role, summary, evidence_url, date_researched, source_quality |
| `hub_capabilities.csv` | a hub connection of a consumer | consumer, capability_id, area, capability, hub, connect (config or code), wired (yes or no), evidence_path |
| `hub_integrations.csv` | a single service a consumer hand-wires | consumer, area, integration, kind, path, covered_by, status (violation or waived), waiver_reason |

`current_hubs` is `name|url|license` entries joined by semicolons. `status` is `builds_on`, `compared` or `no_hub_exists`
(a recorded decision). A connection that is only prepared (`wired` no) does not count.

## What the scorer measures

Given a `Binding` (the consumer's root, which of its solutions fill which area, its core code folder, its ESOI records, and a
probe per area), `hubofhubs.evaluate` answers eight checks per area: registered, by_config, fresh (within 90 days), seam
(one registry in code), selectable (the seam solution has an authoritative metric and two or more implementations), core_clean
(no vendor-specific branch in core, by the static rule in `scan.py`), fake_hub (a fake hub added through the area's
configuration entry works with zero library edits) and no_reinvented. The score is the mean of coverage, integration by
configuration, freshness, code structure and the share of areas free of reinvented integrations.
