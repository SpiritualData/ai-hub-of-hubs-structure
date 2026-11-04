"""The call every retrieval arm answers, and the budgeted choice of units from a ranking."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .units import Corpus, cached_corpus, tokens

DEFAULT_BUDGET = 4000
DEPTH = 100


@dataclass(frozen=True)
class Hit:
    """One unit of context an arm returns: where it is, how it scored and what it costs the reader in tokens."""
    id: str
    file: str
    start: int
    score: float
    tokens: int
    text: str = ""


def within_budget(corpus: Corpus, ranked: Sequence[tuple], budget_tokens: int) -> List[Hit]:
    """The best-ranked units that fit the budget, in rank order: a unit that does not fit is skipped, a later smaller one may still fit."""
    hits: List[Hit] = []
    spent, misses = 0, 0
    for index, score in ranked:
        unit = corpus.units[index]
        if spent + unit.tokens > budget_tokens:
            misses += 1
            if misses >= 25:
                break
            continue
        hits.append(Hit(unit.id, unit.file, unit.start, float(score), unit.tokens, unit.text))
        spent += unit.tokens
    return hits


class Retriever:
    """The shared machinery: prepare a corpus once (cached by its digest), score a query, answer within a budget. An arm sets ``unit`` and
    overrides ``fit`` (build its index) and ``scores`` (``{unit index: score}`` over the candidates it considers)."""
    unit = "chunk"
    depth = DEPTH

    cache_dir: Optional[str] = None

    def __init__(self) -> None:
        self.corpus: Optional[Corpus] = None
        self.fit_seconds = 0.0

    def prepare(self, files: Mapping[str, str], history: Sequence[Mapping[str, Any]] = ()) -> Corpus:
        import time
        from .units import digest_of
        if self.corpus is None or self.corpus.digest != digest_of(files, history, self.unit):
            self.corpus = cached_corpus(files, history, self.unit, getattr(self, 'cache_dir', None))
            started = time.time()
            self.fit(self.corpus)
            self.fit_seconds = time.time() - started
        return self.corpus

    def adopt(self, corpus: Corpus) -> None:
        """Use a corpus another arm already built (the same units, links and priors), fitting only this arm's own index."""
        if self.corpus is not corpus:
            self.corpus = corpus
            self.fit(corpus)

    def fit(self, corpus: Corpus) -> None: ...

    def scores(self, query: str) -> Dict[int, float]:
        raise NotImplementedError

    def ranking(self, query: str) -> List[tuple]:
        return sorted(self.scores(query).items(), key=lambda kv: (-kv[1], kv[0]))[:self.depth]

    def retrieve(self, query: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = DEFAULT_BUDGET,
                 history: Sequence[Mapping[str, Any]] = ()) -> List[Hit]:
        """The units that answer ``query``, best first, within ``budget_tokens``. An empty list means the arm judged no context is needed."""
        if files is not None:
            self.prepare(files, history)
        if self.corpus is None:
            raise ValueError("retrieve needs files the first time (or prepare(files) beforehand)")
        return within_budget(self.corpus, self.ranking(query), budget_tokens)

    def index_bytes(self) -> int:
        """The size of what this arm keeps beyond the corpus text (postings, vectors), an estimate in bytes."""
        return 0


def query_terms(query: str) -> List[str]:
    return list(dict.fromkeys(tokens(query)))
