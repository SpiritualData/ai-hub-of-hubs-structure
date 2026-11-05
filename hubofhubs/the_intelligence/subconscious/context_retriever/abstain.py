"""Knowing when to return nothing, and the model reranker (recorded and replayed, never run in this repository)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from esoi import implementation

from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_world.model_plumbing.vendor_model_caller.interface import ModelCalling
from hubofhubs.the_intelligence.subconscious.context_retriever.base import DEFAULT_BUDGET, Hit, Retriever, query_terms, within_budget
from hubofhubs.the_intelligence.subconscious.context_retriever.fusion import HybridRrf
from hubofhubs.the_intelligence.subconscious.context_retriever.learned import LearnedRerank
from hubofhubs.the_intelligence.subconscious.context_retriever.units import Corpus

COSINE_FLOOR, COSINE_SPAN = 0.45, 0.35    # a bge-small cosine below the floor is noise; the span above it maps to 0..1
CONFIDENCE_FLOOR = 0.663                     # set by evaluation/context_retrieval/calibrate.py on validation questions, before any arm was scored


def confidence(hybrid: HybridRrf, query: str) -> float:
    """How well the corpus answers the query, in 0..1, from two absolute signals: the best cosine and the share of the query's terms that the
    best lexical unit holds. Neither depends on how many units there are, so a flat ranking of weak matches stays low."""
    cosines = hybrid.dense.scores(query)
    best_cosine = max(cosines.values(), default=0.0)
    ranked = hybrid.lexical.ranking(query)
    terms = query_terms(query)
    cover = 0.0
    if ranked and terms:
        unit = hybrid.corpus.units[ranked[0][0]]
        held = set(unit.fields["body"]) | set(unit.fields["title"]) | set(unit.fields["path"])
        cover = sum(t in held for t in terms) / len(terms)
    return 0.5 * min(1.0, max(0.0, (best_cosine - COSINE_FLOOR) / COSINE_SPAN)) + 0.5 * cover


@implementation("context-retriever", "abstaining_learned")
class AbstainingLearned(Retriever):
    """The learned reranker that returns nothing when the corpus does not answer the question: a confidence under ``threshold`` gives an empty list."""
    REQUIRES = (needs.FASTEMBED_LOCAL, needs.FASTEMBED_MODEL, needs.NUMPY, needs.SKLEARN)

    def __init__(self, cache_dir: Optional[str] = None, inner: Any = None, threshold: float = CONFIDENCE_FLOOR) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.inner = inner or LearnedRerank(cache_dir=cache_dir)
        self.threshold = threshold

    def fit(self, corpus: Corpus) -> None:
        self.inner.adopt(corpus)

    def confidence(self, query: str) -> float:
        return confidence(self.inner.hybrid, query)

    def scores(self, query: str) -> Dict[int, float]:
        return self.inner.scores(query)

    def retrieve(self, query: str, files: Optional[Any] = None, budget_tokens: int = DEFAULT_BUDGET, history: Sequence[Any] = (),
                 meta: Optional[Any] = None, request: Optional[Any] = None) -> List[Hit]:
        if files is not None:
            self.prepare(files, history, meta)
        self.begin(request)
        if self.confidence(query) < self.threshold:
            return []
        return within_budget(self.corpus, self.inner.ranking(query), budget_tokens)

    def index_bytes(self) -> int:
        return self.inner.index_bytes()


@implementation("context-retriever", "abstaining_hybrid")
class AbstainingHybrid(AbstainingLearned):
    """The plain hybrid (BM25F and dense by rank fusion) with the same abstention: separates what abstaining adds from what learning adds."""

    def __init__(self, cache_dir: Optional[str] = None, inner: Any = None, threshold: float = CONFIDENCE_FLOOR) -> None:
        super().__init__(cache_dir=cache_dir, inner=inner or HybridRrf(cache_dir=cache_dir), threshold=threshold)

    def confidence(self, query: str) -> float:
        return confidence(self.inner, query)


RERANK_PROMPT = ("You choose which pieces of a codebase a developer needs for a task. Below are numbered candidates (a file and its first lines). "
                 "Reply with only the numbers of the candidates that are needed, most needed first, separated by commas, at most {limit} numbers. "
                 "Reply with the single word none if no candidate is needed. Do not use em dashes and write nothing else.\n\nTask: {query}\n\n{candidates}")
RERANK_POOL, RERANK_KEEP, SNIPPET_CHARS = 30, 8, 240


@implementation("context-retriever", "llm_rerank")
class LlmRerank(Retriever):
    """A model reads the top 30 candidates of the learned reranker (path and 240 characters each) and names the ones the task needs. PAID: one
    model call per query. It is recorded to a cassette and replayed (``esoi run context_retrieval --impl llm_rerank --cassette DIR``); it has
    not been run here."""
    REQUIRES = (needs.FASTEMBED_LOCAL, needs.FASTEMBED_MODEL, needs.NUMPY, needs.SKLEARN)
    PAID = True

    def __init__(self, provider: ModelCalling, cache_dir: Optional[str] = None, inner: Any = None, model: str = "claude-haiku") -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.provider, self.model = provider, model
        self.inner = inner or LearnedRerank(cache_dir=cache_dir)

    def fit(self, corpus: Corpus) -> None:
        self.inner.adopt(corpus)

    def scores(self, query: str) -> Dict[int, float]:
        ranked = self.inner.ranking(query)[:RERANK_POOL]
        listing = "\n".join(f"{n}. {self.corpus.units[i].file}:{self.corpus.units[i].start}  "
                            f"{' '.join(self.corpus.units[i].text[:SNIPPET_CHARS].split())}" for n, (i, _) in enumerate(ranked, 1))
        reply = self.provider.answer([{"role": "user", "content": RERANK_PROMPT.format(limit=RERANK_KEEP, query=query, candidates=listing)}],
                                     model=self.model)
        chosen = [int(n) for n in re.findall(r"\d+", reply if "none" not in reply.lower() else "")][:RERANK_KEEP]
        picked = [ranked[n - 1][0] for n in dict.fromkeys(chosen) if 1 <= n <= len(ranked)]
        return {i: float(len(picked) - rank) for rank, i in enumerate(picked)}

    def index_bytes(self) -> int:
        return self.inner.index_bytes()
