"""Fusing and reranking: reciprocal rank fusion of the lexical and dense first stages, a local feature reranker over the top candidates, and
the priors from links and history (import and co-change neighbours of the best hits, recency)."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from esoi import implementation

from .. import arm_needs as needs
from .base import Retriever, query_terms
from .dense import DenseBgeSmall
from .lexical import Bm25Fielded
from .units import Corpus

RRF_K = 60
TOP_FOR_PRIORS = 8
FEATURES = ("rrf", "bm25", "dense", "coverage", "names", "path", "linked", "cochange", "recent", "length", "header")
# The reranker's weights were written before any arm was scored, from what each feature is for (a cover of the query terms and a match in names
# and paths count most after the fused rank; a long unit costs the reader). No weight was fitted to a score.
RERANK_WEIGHTS = (3.0, 1.5, 2.0, 1.0, 1.5, 1.5, 0.75, 0.75, 0.25, -0.5, 0.0)


def rrf(rankings: Sequence[Sequence[tuple]], k: int = RRF_K) -> Dict[int, float]:
    """Reciprocal rank fusion: each ranking gives a unit ``1 / (k + rank)``."""
    fused: Dict[int, float] = {}
    for ranking in rankings:
        for rank, (index, _) in enumerate(ranking, 1):
            fused[index] = fused.get(index, 0.0) + 1.0 / (k + rank)
    return fused


def scale(values: Dict[int, float]) -> Dict[int, float]:
    top = max(values.values(), default=0.0)
    low = min(values.values(), default=0.0)
    span = (top - low) or 1.0
    return {i: (v - low) / span for i, v in values.items()}


@implementation("retrieve-context", "hybrid_rrf")
class HybridRrf(Retriever):
    """BM25F and the dense arm fused by reciprocal rank (k = 60): a unit either one ranks well comes up, one both rank well comes first."""
    REQUIRES = (needs.FASTEMBED_LOCAL, needs.FASTEMBED_MODEL, needs.NUMPY)

    def __init__(self, cache_dir: Optional[str] = None, lexical: Any = None, dense: Any = None) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.lexical = lexical or Bm25Fielded()
        self.dense = dense or DenseBgeSmall(cache_dir=cache_dir)

    def fit(self, corpus: Corpus) -> None:
        self.lexical.adopt(corpus)
        self.dense.adopt(corpus)

    def scores(self, query: str) -> Dict[int, float]:
        return rrf([self.lexical.ranking(query), self.dense.ranking(query)])

    def index_bytes(self) -> int:
        return self.lexical.index_bytes() + self.dense.index_bytes()


class Candidates:
    """The features of each candidate unit for one query, shared by the feature reranker and the learned reranker."""

    def __init__(self, hybrid: HybridRrf, query: str, corpus: Corpus, depth: int = 100, minus: Sequence[str] = ()):
        self.corpus, self.query = corpus, query
        lexical = dict(hybrid.lexical.ranking(query))
        dense = dict(hybrid.dense.ranking(query))
        fused = rrf([sorted(lexical.items(), key=lambda kv: -kv[1]), sorted(dense.items(), key=lambda kv: -kv[1])])
        pool = sorted(fused, key=lambda i: -fused[i])[:depth]
        top_files = list(dict.fromkeys(corpus.units[i].file for i in pool))[:TOP_FOR_PRIORS]
        weight = {f: 1.0 / (1 + r) for r, f in enumerate(top_files)}
        linked: Dict[str, float] = {}
        cochanged: Dict[str, float] = {}
        for f, w in weight.items():
            for n in corpus.neighbours(f):
                linked[n] = linked.get(n, 0.0) + w
            held = set(minus)      # a training query leaves its own commit out of the co-change counts
            share = 1.0 / max(len(held) - 1, 1) if f in held else 0.0
            for n, c in corpus.cochange.get(f, {}).items():
                c -= share if n in held else 0.0
                if c > 0:
                    cochanged[n] = cochanged.get(n, 0.0) + w * c
        for f in list(linked) + list(cochanged):     # a neighbour of a hit may not be retrieved at all: its best lexical unit joins the pool
            best = max(corpus.by_file.get(f, ()), key=lambda i: lexical.get(i, 0.0), default=None)
            if best is not None and best not in pool:
                pool.append(best)
        terms = query_terms(query)
        lex_top = max(lexical.values(), default=1.0) or 1.0
        self.pool = pool
        self.fused, self.dense_scores = scale(fused), scale(dense) if dense else {}
        self.matrix: List[List[float]] = []
        link_top = max(linked.values(), default=0.0) or 1.0
        co_top = max(cochanged.values(), default=0.0) or 1.0
        for i in pool:
            u = corpus.units[i]
            body, names, path = set(u.fields["body"]), set(u.fields["title"]), set(u.fields["path"])
            n = len(terms) or 1
            self.matrix.append([
                self.fused.get(i, 0.0), lexical.get(i, 0.0) / lex_top, self.dense_scores.get(i, 0.0),
                sum(t in body or t in names for t in terms) / n, sum(t in names for t in terms) / n, sum(t in path for t in terms) / n,
                linked.get(u.file, 0.0) / link_top, cochanged.get(u.file, 0.0) / co_top, corpus.recency.get(u.file, 0.0),
                math.log(u.tokens) / math.log(2000), 1.0 if u.header else 0.0])


@implementation("retrieve-context", "feature_rerank")
class FeatureRerank(Retriever):
    """The top 100 of the hybrid reranked by a fixed linear combination of eleven local features (fused rank, BM25, cosine, term cover, name
    and path matches, import and co-change neighbours of the best hits, recency, length), written before scoring."""
    REQUIRES = (needs.FASTEMBED_LOCAL, needs.FASTEMBED_MODEL, needs.NUMPY)
    weights = RERANK_WEIGHTS

    def __init__(self, cache_dir: Optional[str] = None, hybrid: Any = None) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.hybrid = hybrid or HybridRrf(cache_dir=cache_dir)

    def fit(self, corpus: Corpus) -> None:
        self.hybrid.adopt(corpus)

    def candidate_scores(self, candidates: Candidates) -> List[float]:
        return [sum(w * f for w, f in zip(self.weights, row)) for row in candidates.matrix]

    def scores(self, query: str) -> Dict[int, float]:
        c = Candidates(self.hybrid, query, self.corpus)
        return dict(zip(c.pool, self.candidate_scores(c)))

    def index_bytes(self) -> int:
        return self.hybrid.index_bytes()


@implementation("retrieve-context", "feature_rerank_no_priors")
class FeatureRerankNoPriors(FeatureRerank):
    """The same reranker with the link, co-change and recency features switched off: the ablation of the non-text priors."""
    weights = RERANK_WEIGHTS[:6] + (0.0, 0.0, 0.0) + RERANK_WEIGHTS[9:]
