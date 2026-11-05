"""Metadata-aware arms: the selected arm (the hybrid behind the confidence gate) with item metadata and the request's time and focus.

An item MAY carry a timestamp, a kind, an author role and home groupings (``units.ITEM_META``), and a request a timestamp and a focus. Four
arms read them, all free (no model call), each a small change to the same ranking so what the metadata adds can be told apart:

* ``abstaining_recency``: older items give way to newer ones (a half-life on the age of an item relative to the request).
* ``abstaining_affinity``: an item whose home is the request's focus is preferred; one from elsewhere is only nudged down (soft, ranking only,
  ``hubofhubs.recall.affinity_tags``), so it can still answer when it is exactly what the request needs.
* ``abstaining_aware``: both, and a newer item supersedes an older one that says nearly the same thing (a fact updated since).
* ``abstaining_fenced``: the hard fence for comparison: an item outside the request's focus is gone from the candidates
  (``hubofhubs.recall.scope_tags`` semantics), however well it matches.

An item or request without metadata ranks exactly as the plain hybrid does. The constants were written before any arm was scored on the
kinds that exercise them and were not fitted to a score. ``live_scan`` is the diagnostic bound for source access: it reads every source at
request time, which the source meter charges for.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from esoi import implementation

from ..recall.affinity_tags import affinity_factor
from ..recall.scope_tags import as_tag_list, scope_tags_allow
from .abstain import AbstainingHybrid, CONFIDENCE_FLOOR
from .base import DEFAULT_BUDGET, Hit, Retriever, query_terms, within_budget
from .fusion import scale
from .units import Corpus, age_days

HALF_LIFE_DAYS = 180.0          # an item this much older than another loses half of the recency edge
RECENCY_EDGE = 0.20             # the most a very old item loses: its score times 0.8 at the limit
HOME_BOOST, AWAY_FACTOR = 1.3, 0.8
SUPERSEDE_COSINE = 0.85         # two items this alike, the newer by a day or more, are one fact told twice
SUPERSEDE_FACTOR = 0.5
SUPERSEDE_TOP = 12


class AwareHybrid(AbstainingHybrid):
    """The abstaining hybrid whose ranking reads item metadata. Subclasses switch the readings on."""
    recency = home = supersede = fence = False

    def tags_of(self, unit) -> List[str]:
        return as_tag_list(self.corpus.meta_of(unit.file).get("affinity_tags"))

    def reranked(self, query: str) -> List[tuple]:
        corpus: Corpus = self.corpus
        base = scale(self.inner.scores(query))
        focus, asked = as_tag_list(self.request.get("affinity_tags")), self.request.get("timestamp")
        out: Dict[int, float] = {}
        for index, score in base.items():
            unit = corpus.units[index]
            meta = corpus.meta_of(unit.file)
            factor = 1.0
            if self.fence and not scope_tags_allow(self.tags_of(unit), focus):
                continue
            if self.home:
                factor *= affinity_factor(self.tags_of(unit), focus, home_boost=HOME_BOOST, away_factor=AWAY_FACTOR)
            if self.recency:
                age = age_days(meta.get("timestamp"), asked)
                if age is not None:
                    factor *= (1 - RECENCY_EDGE) + RECENCY_EDGE * 0.5 ** (max(age, 0.0) / HALF_LIFE_DAYS)
            out[index] = score * factor
        ranked = sorted(out.items(), key=lambda kv: (-kv[1], kv[0]))[:self.depth]
        return self.supersede_older(ranked) if self.supersede else ranked

    def supersede_older(self, ranked: List[tuple]) -> List[tuple]:
        corpus, matrix = self.corpus, self.inner.dense.matrix
        top = ranked[:SUPERSEDE_TOP]
        demoted = set()
        for a, (i, _) in enumerate(top):
            for j, _ in top[a + 1:]:
                ui, uj = corpus.units[i], corpus.units[j]
                if ui.file == uj.file:
                    continue
                gap = age_days(corpus.meta_of(ui.file).get("timestamp"), corpus.meta_of(uj.file).get("timestamp"))   # positive: i is older than j
                if gap is None or abs(gap) < 1.0 or float(matrix[i] @ matrix[j]) < SUPERSEDE_COSINE:
                    continue
                demoted.add(i if gap > 0 else j)
        again = [(i, s * (SUPERSEDE_FACTOR if i in demoted else 1.0)) for i, s in ranked]
        return sorted(again, key=lambda kv: (-kv[1], kv[0]))

    def retrieve(self, query: str, files: Optional[Any] = None, budget_tokens: int = DEFAULT_BUDGET, history: Sequence[Any] = (),
                 meta: Optional[Any] = None, request: Optional[Any] = None) -> List[Hit]:
        if files is not None:
            self.prepare(files, history, meta)
        self.begin(request)
        if self.confidence(query) < self.threshold:
            return []
        return within_budget(self.corpus, self.reranked(query), budget_tokens)


@implementation("retrieve-context", "abstaining_recency")
class AbstainingRecency(AwareHybrid):
    """The abstaining hybrid with a recency factor: an item loses up to a fifth of its score by its age relative to the request (half-life 180 days)."""
    recency = True


@implementation("retrieve-context", "abstaining_affinity")
class AbstainingAffinity(AwareHybrid):
    """The abstaining hybrid with soft affinity: an item at home in the request's focus times 1.3, an item from elsewhere times 0.8, never hidden."""
    home = True


@implementation("retrieve-context", "abstaining_aware")
class AbstainingAware(AwareHybrid):
    """Recency, soft affinity and supersession together: of two near-identical items the older one is halved."""
    recency = home = supersede = True


@implementation("retrieve-context", "abstaining_fenced")
class AbstainingFenced(AwareHybrid):
    """The hard-fence comparison: items outside the request's focus are removed from the candidates, as a scope fence would."""
    fence = True


@implementation("retrieve-context", "live_scan")
class LiveScan(Retriever):
    """The diagnostic bound for source access: no index, every request reads every source (one call and one record each) and ranks whole files
    by how often the request's terms occur. It shows what reading live costs; it is accurate only as far as counting words is."""
    unit = "file"
    REQUIRES = ()

    def scores(self, query: str) -> Dict[int, float]:
        from .units import tokens
        terms = set(query_terms(query))
        out: Dict[int, float] = {}
        for path, indexes in self.corpus.by_file.items():
            counts = Counter(tokens(self.source.read(self.corpus, path)))
            hit = sum(1 + counts[t] ** 0.5 for t in terms if counts[t])
            if hit:
                out[indexes[0]] = hit / (1 + len(terms))
        return out
