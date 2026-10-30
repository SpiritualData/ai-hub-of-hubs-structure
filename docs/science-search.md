# Scholarly search: the OpenAlex arm of the know-the-world seat

Status 2026-10-30: built and tested offline, **not selected** (no measurement yet), not measured against the baseline.
Descriptive wording in the records stays the owner's; the implementation row reads "unconfirmed: for Joshua to confirm."

## What it is

`hubofhubs.science.openalex.OpenAlexWorks` is an implementation of the `know-the-world` seat (`@implementation("know-the-world",
"openalex")`), beside `web_research`. It finds scholarly works and returns what a citation needs: title, authors, year, venue, DOI,
citation count, an abstract rebuilt from OpenAlex's inverted index, and a landing link. `hubofhubs.science.crossref.lookup_doi`
is a small helper that asks Crossref whether a DOI exists and what it is registered as. Port values (`Work`, `WorksResult`,
`ScholarlyError`) are in `hubofhubs.ports.scholarly`.

**Why the existing seat and not a new one.** `WorldKnowing` already is "look up what the world says and return observations a
reader can cite" (`describe`, `search`, `fetch`). A scholarly arm fits it: `search` returns one `Observation` whose hits are
works, `fetch` reads one work by DOI. A second seat would split the metric of the Science seat for no gain. The typed method
`find_works(query, year_from, year_to, open_access_only, sort_by_citations, limit)` is an extra on the arm, for a consumer that
wants the filters; the seat methods use the constructor defaults. If measurement later shows the filters matter, that is the
moment to propose a narrower `ScholarlySearching` seat (propose to Joshua).

**Marginal value claim.** None yet. The baseline is "none: provider-native plus the harness as is", here the web search read.
The arm is registered so it can be measured against that on the same cases; selection follows the seat's metric, never preference.

## Use

```python
from hubofhubs.science.openalex import OpenAlexWorks
arm = OpenAlexWorks(api_key=key_from_your_config, mailto=contact_from_your_config, daily_limit=200)
observation = arm.search("aerobic fitness knee injury")          # text with numbered citation lines, hits as dicts
result = arm.find_works("aerobic fitness knee injury", year_from=2015, open_access_only=True)   # typed WorksResult
```

Install the extra: `pip install hubofhubs[science]` (it is `httpx`, imported only when the default transport runs). The
hub reads no environment: key, contact address, limits and the transport are arguments. A failure never raises; it is a
`ScholarlyError` with a `kind` (`rate_limited`, `budget`, `key_not_activated`, `unauthorized`, `bad_request`, `not_found`,
`server`, `timeout`, `network`, `bad_response`, `missing_dependency`, `not_a_doi`) and, from the seat methods, an `error`
observation. The result text states "Cite only the works listed here" and says "No DOI listed" for a work without one, so a
reader has nothing to fill in from memory.

Politeness and limits: calls are spaced by `min_interval` (default 0.1 s, the keyless limit is 10 a second); `daily_limit` caps the
real calls one instance makes per UTC day; identical requests are answered from a per-instance cache (`cache_ttl`, default one
day) and cost nothing; every call has a timeout (default 10 s). The key travels in an `Authorization: Bearer` header, never in
the URL.

## Facts relied on (OpenAlex documentation read 2026-10-30; the research report that first recorded them is private)

- A free key is needed for real use: $1 a day with a key, $0.10 a day without; 10 requests a second without, 30 with. 429 means the
  daily allowance or the per-second limit. An unactivated key answers 403 `key_not_activated`.
  https://help.openalex.org/api/authentication (the older registry wording "no key, 100,000 requests a day" is out of date)
- Cost per 1,000 calls: search $1, list with filter $0.10, one record by id or DOI free. A search is about 1,000 a day on the free
  key. https://help.openalex.org/access/example-costs
- Text search `search.title_abstract_keywords`; filters `is_oa`, `from_publication_date`, `to_publication_date`; `select`,
  `per_page` (this arm caps at 25). https://help.openalex.org/api/searching and https://help.openalex.org/api/filtering
- A key can be requested for a user with `POST https://api.openalex.org/api-keys` and the user's own email; it works once they
  click the emailed link. The arm never does this; a person obtains the key.
- Crossref: `GET https://api.crossref.org/works/{doi}`, polite pool by `mailto` parameter or agent header (rates: public 5, polite
  10; the time unit is not stated on the page, which was updated 2025-10-16).
  https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

## Not verified

- Whether OpenAlex still honours `mailto` (it is absent from the current documentation; a request carrying it returned 200).
- Retraction filtering (`is_retracted`) and the exact semantics of `type` for preprints: not used.
- The Crossref limit change of 2026-07-21 is quoted from the research report, not re-fetched.
- Coverage of weakly indexed literature (the research report counted phrase hits; those counts are noisy and unmeasured as recall).

## Tests

`tests/test_science_openalex.py` uses recorded responses in `tests/fixtures/` (OpenAlex works search and DOI lookup, Crossref
work, all recorded 2026-10-30 with author names replaced by placeholders). Error replies the recording did not capture are shaped
from the documented error pages and say so in the test. No test touches the network.
