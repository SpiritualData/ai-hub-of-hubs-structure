"""``focus_first``: whole-item BM25F with the request's focus first. Items at home in the focus come before every other item (soft affinity, ranking only,
``context_cards.affinity_tags``); an item outside the request's scope is gone (the hard fence, ``context_cards.scope_tags``); an item from another home is shown only
when it matches the request about as well as the best item does. An item flagged ``overview`` (a short statement of what the focus is) at home in the focus is always
offered, because it says what the person is after; the other items at home need a word in common with the request, and when the request touches the focus at all the
most recent ones fill the list up to ``FILL_HOME`` so the latest of what is known comes along.

A relevance floor comes first: an item counts only when it bears on the request, which means it shares at least ``MIN_SHARED`` distinct request terms (one stray common
word such as "time" or "plot" is not evidence), or, for an item at home in the focus, the request is about the focus itself (it names the focus, says "my"/"our", or is borne on by a home item with at least
``MIN_SHARED`` terms).
A request that nothing bears on gets no item at all, not even the overview: the overview is offered because the request is about the focus, never in its place.
The constants were written before any case was scored."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation

from hubofhubs.the_intelligence.subconscious.context_retriever.base import DEFAULT_BUDGET, Hit, within_budget
from hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.affinity_tags import affinity_factor
from hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.scope_tags import as_tag_list, scope_tags_allow
from hubofhubs.the_intelligence.subconscious.context_retriever.lexical import Bm25WholeFiles
from hubofhubs.the_intelligence.subconscious.context_retriever.units import parse_time, tokens

AWAY_SHARE = 0.6       # an item from another home needs this share of the best score to be shown
MIN_SHARED = 2         # distinct request terms an item must share with the request to bear on it (one stray common word is not enough)
FIRST_PERSON = re.compile(r"\b(my|our|mine|myself)\b", re.IGNORECASE)
FILL_HOME = 3          # when the request touches the focus, at least this many home items come along (the newest)


@implementation("context-retriever", "focus_first")
class FocusFirst(Bm25WholeFiles):
    """Whole-item BM25F, the request's focus first, the scope fence kept, the focus's overview always offered."""
    REQUIRES = ()

    def retrieve(self, query: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = DEFAULT_BUDGET, history: Sequence[Any] = (),
                 meta: Optional[Mapping[str, Mapping[str, Any]]] = None, request: Optional[Mapping[str, Any]] = None) -> List[Hit]:
        if files is not None:
            self.prepare(files, history, meta)
        self.begin(request)
        corpus = self.corpus
        focus, fence = as_tag_list(self.request.get("affinity_tags")), self.request.get("scope_tags")
        raw: Dict[int, float] = self.scores(query)
        asked = set(tokens(query))
        seen = []
        for unit in corpus.units:
            item = corpus.meta_of(unit.file)
            if not scope_tags_allow(item.get("scope_tags"), fence):
                continue
            at_home = bool(focus) and affinity_factor(item.get("affinity_tags"), focus, home_boost=2.0, away_factor=1.0) > 1.0
            seen.append((unit, item, at_home, len(asked & set(tokens(unit.text)))))
        about_focus = (bool(FIRST_PERSON.search(query or "")) or any(t in asked for tag in focus for t in tokens(tag.split(":", 1)[-1]))
                       or any(home and shared >= MIN_SHARED for _, _, home, shared in seen))
        rows = []
        for unit, item, at_home, shared in seen:
            if shared < MIN_SHARED and not (at_home and about_focus):
                continue         # the relevance floor: nothing in this item bears on the request
            rows.append((unit.index, at_home, bool(item.get("overview")), raw.get(unit.index, 0.0), parse_time(item.get("timestamp")) or 0.0))
        best = max((score for _, _, _, score, _ in rows), default=0.0)
        touched = any(home and score > 0 for _, home, _, score, _ in rows)
        chosen = []
        for index, home, overview, score, stamp in rows:
            if home and (overview or score > 0):
                chosen.append((index, True, overview, score, stamp))
            elif not home and best > 0 and score >= AWAY_SHARE * best:
                chosen.append((index, False, False, score, stamp))
        if touched:
            taken = {row[0] for row in chosen}
            fill = sorted((row for row in rows if row[1] and row[0] not in taken), key=lambda row: (-row[4], row[0]))
            chosen += [(i, True, False, s, t) for i, _, _, s, t in fill[:max(0, FILL_HOME - sum(1 for c in chosen if c[1]))]]
        ranked = sorted(chosen, key=lambda row: (not row[1], not row[2], -row[3], -row[4], row[0]))
        return within_budget(corpus, [(index, score) for index, _, _, score, _ in ranked], budget_tokens)
