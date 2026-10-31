"""openalex_semantic -- the OpenAlex arm of ``know-the-world`` that matches by meaning instead of keywords.

Fact this relies on, read from OpenAlex's own documentation on 2026-10-31 (https://help.openalex.org/api/semantic-search.md and
https://help.openalex.org/api/searching.md): ``GET /works?search.semantic=<text>`` embeds the title and abstract of every work with
GTE Large EN and returns the works closest to the embedded query by cosine similarity. It is meant for long inputs (an abstract,
a grant aim). Up to 2,000 characters of the query are used; at most 50 results; 1 request per second; it cannot be combined with
another search parameter or with ``rerank``; it works keyless (a search costs the same as a keyword search, about $0.001).

Everything else (key, limits, cache, filters, citation lines, errors) is inherited from the keyword arm, ``OpenAlexWorks``.
"""
from __future__ import annotations

from esoi import implementation

from .openalex import OpenAlexWorks

SEMANTIC_PARAM = "search.semantic"
MAX_QUERY_CHARS = 2000
MIN_INTERVAL_SECONDS = 2.0   # documented limit is 1 request a second; a 40-case run at 1 s was answered with HTTP 429 for 11 cases, so the arm waits 2 s


@implementation("know-the-world", "openalex_semantic")
class OpenAlexSemantic(OpenAlexWorks):
    """Searches the scholarly literature by meaning (OpenAlex semantic search) and returns works a reader can cite."""

    search_param = SEMANTIC_PARAM

    def __init__(self, *, min_interval: float = MIN_INTERVAL_SECONDS, **settings) -> None:
        super().__init__(min_interval=min_interval, **settings)

    def prepare(self, query: str) -> str:
        return " ".join(query.split())[:MAX_QUERY_CHARS]

    def describe(self) -> str:
        return "scholarly works search by meaning (OpenAlex semantic search, " + ("with a key" if self.api_key else "no key, small daily allowance") + ")"
