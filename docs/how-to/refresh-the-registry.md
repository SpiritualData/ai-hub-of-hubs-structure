# The weekly refresh

Each area is researched again before its `last_researched` date is 90 days old, and a consumer's autopilot does one area a day,
oldest first. The refresh of an area is one application of Learning's review: a small systematic review at standard size
(the [research standard](https://github.com/JoshuaMathias/evolvable-structure/blob/main/docs/reference/knowledge-search-standard.md) of the ESOI library),
whose record is stored beside the registry and which the area's findings point back to. The instruction, with no paid model calls (a subscription model and web search only):

0. **Run it as a review.** `system["the-learning"].review(**review_store.area_request(area_row), today=...)` takes the area's question, its
   weight (a registry area selects what a consumer connects, so the size is standard), the area's candidates and its refresh interval of 90 days;
   it fixes the method, searches Web Search and The Science, screens with counts, grades each item, decides for each candidate (adopt, reject or defer, with a
   reason) and names what each item changed. Keep what it returns (`review_store.store(record)` writes `research.csv` and `research_items.csv` beside the registry,
   superseding the area's earlier review). Then do steps 2 to 4 with its items as the source of each finding's `candidate`, `url`, `license`, `source_quality`,
   `adoption` and `adoption_reason`. Each finding names its review in the `research_id` column of `hub_findings.csv`: after step 3,
   `review_store.link_findings(record["research"]["research_id"], record["research"])` writes it on the area's rows of that day (`store` does the same for rows already there),
   and `review_store.finding_review(finding_row)` reads it, falling back to the area and the day it was researched for rows written before the column.
   At standard and full size the kept pages are opened through The Science seat (`verified` is `opened` or `cross-checked`); an item read only as a result snippet is
   `snippet` and is graded C at most, so only an opened item can support an `adoption` of `arm`.

1. Read the stale or oldest area from the scorer's output.
2. Search for open-source hubs for the area released or changed since `last_researched`. Prefer official repositories and
   documentation; cite the URL and date of each. Look for what a consumer could connect by configuration and for alternatives
   to compare as arms.
3. Replace the area's rows in `hub_findings.csv` (ids `<prefix>-1`, `<prefix>-2` and so on, where the prefix is the area's
   `finding_id` in `hubs.csv`; at least 2 candidates unless the area names a single one, and at most 16, since a sub-solution
   area may weigh many; split an area that needs more; license, role, one line, evidence URL, today's date, and
   say when a license is unconfirmed), then set `last_researched`, `researched_by` and `recommendation` in `hubs.csv`, and the machine-readable `call` that the recommendation's first decision states (adopt, coexist, keep, watch or avoid; leave it blank only when you cannot tell, and a blank counts as coexist). Update the
   consumer's rows in `hub_capabilities.csv` (a hub connection, never a single service) and `hub_integrations.csv`. Never record
   adoption the consumer's code does not show.
   For an area that maps to a solution, every finding also carries `adoption` (`arm`: an implementation of that solution is built on it, named in `adopted_as`; `part`: a library, protocol or behaviour of it is used, named in `adopted_as` with where; `not_adopted`: neither) and `adoption_reason` (the licence checked at the source, the language, whether it can be separated from its own agent, how it fits the solution's contract); `tests/test_adoption_and_entry_guards.py` pins it for every area researched from 2026-11-11 and for the areas already decided.
4. Run the consumer's scorer and `python3 scripts/status.py` (it rewrites the README seat table and `docs/reference/registry.md`), then `esoi hygiene`. No names, ids, emails or machine paths; no
   em dashes.
5. Commit only those files. If a recommendation is worth building, raise a decision rather than building it unasked.

## What learning is due

An autopilot asks the assembled Learning solution: `system["the-learning"].due_reviews("2026-11-10")` (the date is optional) returns a list, most overdue
first, of `{"kind", "id", "question", "links", "due_on", "days_overdue", "request"}`, where `kind` is `review` (an open review past its `refresh_on`),
`experiment` (a running experiment past its `reevaluate_time`, the older `reevaluate_on` is read too) or `registry-area` (an area older than ninety days or never recorded as a review), and `request` is the
instruction to run for it. The weekly refresh is declared as standing work: `system["the-learning"].standing_schedule(last_run)` returns a schedule
(`name` `learning-weekly-refresh`, `cadence` weekly, `request`) that Proactivity reads, so `proactive([schedule, ...], now)` says when to ask `due_reviews`.

Public evidence is refreshed in the same pass: for the area, re-open each `source_url` in `hubofhubs/registry/hub_evidence.csv`,
update `value` and `date_checked`, add rows for new independent sources, and keep conflicting sources side by side. Enter no
number you could not confirm on its page. How a row is judged is in [public evidence](../explanation/public-evidence.md).
