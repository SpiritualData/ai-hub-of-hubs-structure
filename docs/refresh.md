# The weekly refresh

Each area is researched again before its `last_researched` date is 90 days old, and a consumer's autopilot does one area a day,
oldest first. The instruction, with no paid model calls (a subscription model and web search only):

1. Read the stale or oldest area from the scorer's output.
2. Search for open-source hubs for the area released or changed since `last_researched`. Prefer official repositories and
   documentation; cite the URL and date of each. Look for what a consumer could connect by configuration and for alternatives
   to compare as arms.
3. Replace the area's rows in `hub_findings.csv` (2 to 4 candidates, license, role, one line, evidence URL, today's date, and
   say when a license is unconfirmed), then set `last_researched`, `researched_by` and `recommendation` in `hubs.csv`. Update the
   consumer's rows in `hub_capabilities.csv` (a hub connection, never a single service) and `hub_integrations.csv`. Never record
   adoption the consumer's code does not show.
4. Run the consumer's scorer and `python3 scripts/status.py`, then `esoi hygiene`. No names, ids, emails or machine paths; no
   em dashes.
5. Commit only those files. If a recommendation is worth building, raise a decision rather than building it unasked.
