# Changelog

## Unreleased

- **Scholarly search: an OpenAlex arm of the `know-the-world` seat (2026-10-30; built offline, not selected, not measured).** `hubofhubs.science.openalex.OpenAlexWorks` (`@implementation("know-the-world", "openalex")`, extra `science`) searches works with year and open-access filters and returns title, authors, year, venue, DOI, citations, an abstract rebuilt from the inverted index and a landing link, with a typed error per failure, a cache, spacing and a daily cap. `hubofhubs.science.crossref.lookup_doi` checks a DOI. Port values in `hubofhubs.ports.scholarly`. Key and contact address are arguments. See `docs/science-search.md`.
