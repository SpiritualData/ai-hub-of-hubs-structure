"""openalex_semantic_and_web -- the ``know-the-world`` arm that asks a scholarly semantic search and a broader web search and merges them.

Public research favours combining a semantic paper search with a broader one (``docs/explanation/what-public-research-says.md``). Both arms answer the same
question; their ranked hit lists are interleaved (scholarly first, then web, then the second of each, ...), duplicates are dropped
(by DOI when both hits carry one, else by the normalized title: lower case, letters and digits only), and the first ``max_results`` are kept.
The merged text lists those hits and then carries the web arm's own summary text unchanged, because a web arm answers in prose. Either
arm failing leaves the other's answer; both failing is an error observation. ``fetch`` goes to the scholarly arm for a DOI and to the web arm
for anything else.
"""
from __future__ import annotations

import re
from itertools import zip_longest
from typing import List, Optional, Union

from esoi import implementation

from ..ports.retrieval import Observation
from ..seats import SearchBackend
from ..websearch.research import WebResearchAdapter
from .openalex import doi_of
from .openalex_semantic import OpenAlexSemantic
from .. import arm_needs as needs

MAX_RESULTS = 5


def normalized_title(title: object) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(title or "").lower()).split())


def interleave(first: List[dict], second: List[dict], limit: int) -> List[dict]:
    """Alternate the two ranked lists, drop a hit already kept (same DOI, else same normalized title), keep ``limit``."""
    merged: List[dict] = []
    seen_doi, seen_title = set(), set()
    for pair in zip_longest(first, second):
        for hit in pair:
            if not hit:
                continue
            doi, title = doi_of(hit.get("doi")), normalized_title(hit.get("title"))
            if (doi and doi in seen_doi) or (title and title in seen_title):
                continue
            doi and seen_doi.add(doi)
            title and seen_title.add(title)
            merged.append(hit)
    return merged[:max(1, limit)]


@implementation("know-the-world", "openalex_semantic_and_web")
class SemanticAndWeb:
    """Merges a scholarly semantic search and a web search into one observation."""
    REQUIRES = (needs.OPENALEX_API, needs.HTTPX_SCIENCE, needs.HTTPX, needs.FILELOCK, needs.TRAFILATURA, needs.PYPDF)     # the search-backend seat supplies the web search

    def __init__(self, backend: SearchBackend, *, api_key: str = "", mailto: str = "", max_results: int = MAX_RESULTS,
                 scholarly=None, web=None) -> None:
        """The needs are the ``search-backend`` seat, which the web arm runs on, and the OpenAlex key and contact address. The two
        arms are built here from them; ``scholarly`` and ``web`` hand in ready arms instead (plain collaborators, not seat needs)."""
        self.scholarly = scholarly or OpenAlexSemantic(api_key=api_key, mailto=mailto)
        self.web = web or WebResearchAdapter(backend)
        self.max_results = max_results

    def describe(self) -> str:
        return f"{self.scholarly.describe()} merged with {self.web.describe()}"

    def search(self, queries: Union[str, List[str]], *, max_results: Optional[int] = None, fresh: bool = False) -> Observation:
        limit = max_results or self.max_results
        answers = [arm.search(queries, max_results=limit, fresh=fresh) for arm in (self.scholarly, self.web)]
        good = [a for a in answers if a.kind != "error"]
        if not good:
            return Observation(kind="error", error="; ".join(a.error or "no answer" for a in answers))
        hits = interleave(*(a.hits if a.kind != "error" else [] for a in answers), limit)
        lines = [f"COMBINED RESULTS ({len(hits)} of {sum(len(a.hits) for a in good)} hits, scholarly and web interleaved):"]
        for i, hit in enumerate(hits, 1):
            lines.append(f"{i}. {hit.get('title') or '(untitled)'} | {hit.get('doi') and 'DOI ' + str(hit['doi']) or hit.get('url') or ''} | {hit.get('source', '')}")
        web = answers[1]
        if web.kind != "error" and web.text:
            lines += ["", "Web summary and results:", web.text]
        return Observation(kind="query", rel_path="combined:" + (queries if isinstance(queries, str) else " | ".join(queries))[:80],
                           text="\n".join(lines), hits=hits)

    def fetch(self, url: str, *, focus: Optional[str] = None, fresh: bool = False, full: bool = False,
              part: Optional[int] = None) -> Observation:
        arm = self.scholarly if doi_of(url) else self.web
        return arm.fetch(url, focus=focus, fresh=fresh, full=full, part=part)
