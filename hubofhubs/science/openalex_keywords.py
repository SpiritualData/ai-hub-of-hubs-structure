"""openalex_keywords and openalex_keywords_model -- OpenAlex keyword search after the question is cut down to a short keyword query.

OpenAlex's keyword search (``search.title_abstract_keywords``) returned little or nothing for a full natural-language question
(see ``evaluation/know_the_world/README.md``), so these arms rewrite the question first:

* ``openalex_keywords``: a deterministic rewrite with no model. Question words and stop words are removed (the stop list of
  ``hubofhubs.recall.text_sampling.keywords_from_text``, plus the generic words of a literature request), duplicates are dropped, and the
  ``max_terms`` longest of the rest are kept in the order they were written (a longer word is usually the more specific one).
* ``openalex_keywords_model``: a model writes the keyword query through the ``model-call`` seat (the consumer chooses the model and tier);
  when the model fails or returns nothing, the deterministic rewrite is used, so the arm never searches on an empty query.
"""
from __future__ import annotations

import re
from typing import List

from esoi import implementation

from ..recall.text_sampling import keywords_from_text
from ..seats import ModelCall
from .openalex import OpenAlexWorks

#: Words that fill a literature request without naming its subject (on top of the stop words of ``keywords_from_text``).
GENERIC = frozenset("""
paper papers work works study studies research researchers article articles literature approach approaches method methods technique
techniques recent recently existing explore explores explored exploring propose proposed introduces introduced present presents
using used use uses based any there whether many much could please find looking recommend suggest known related relevant address
addresses addressing investigate investigates investigating focus focuses towards potential include includes including involve involves
highlight highlights necessity relationship performance improvement provide provides specifically particular especially context interested
regarding concerning show shows demonstrate demonstrates tasks task aspects aspect areas area direct
""".split())
MAX_TERMS = 5
MAX_QUERY_CHARS = 200

REWRITE_PROMPT = """\
Rewrite this literature-search question as a short keyword query for a scholarly search engine that matches words in titles and
abstracts. Use 3 to 6 specific technical terms or short phrases, no question words, no filler. Do not use em dashes. Output only the query.

Question: {question}
"""


def keyword_query(question: str, max_terms: int = MAX_TERMS) -> str:
    """The question as a short keyword query, with no model. Empty when nothing but filler is left."""
    seen: List[str] = []
    for word in keywords_from_text(question):
        if word not in GENERIC and word not in seen:
            seen.append(word)
    kept = set(sorted(seen, key=len, reverse=True)[:max(1, max_terms)])
    return " ".join(w for w in seen if w in kept)


@implementation("know-the-world", "openalex_keywords")
class OpenAlexKeywords(OpenAlexWorks):
    """OpenAlex keyword search over a deterministic keyword rewrite of the question; no model is called."""

    def prepare(self, query: str) -> str:
        return keyword_query(query) or query


@implementation("know-the-world", "openalex_keywords_model")
class OpenAlexKeywordsModel(OpenAlexWorks):
    """OpenAlex keyword search over a keyword query a model wrote; the model comes from the ``model-call`` seat.

    ``tier`` is the tier asked of the seat. A failed or empty reply falls back to the deterministic rewrite.
    """

    def __init__(self, model: ModelCall, *, tier: str = "", **settings) -> None:
        super().__init__(**settings)
        self.model, self.tier = model, tier

    def prepare(self, query: str) -> str:
        try:
            written = " ".join(re.sub(r"[\"'`]", " ", str(self.model.complete(REWRITE_PROMPT.format(question=query.strip()), self.tier) or "")).split())
        except Exception:  # noqa: BLE001  a model failure is a fallback, never a crash
            written = ""
        return written[:MAX_QUERY_CHARS] or keyword_query(query) or query
