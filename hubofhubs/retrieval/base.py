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


class SourceMeter:
    """Counts what an arm reads from the live sources while it answers one request: source calls, records and bytes. The corpus's texts are the
    sources; an arm that answers from the index it built beforehand never calls ``read`` and counts 0, an arm that scans sources per request
    pays per read (the evaluation folds the counts into the case's cost at a stated unit price). ``scopes`` is what the request may read
    (``scope_tags``); a read or a returned item outside it counts as out of scope."""

    def __init__(self, corpus_ref=None) -> None:
        self.calls = self.records = self.bytes = self.out_of_scope = 0
        self.seen: set = set()
        self.allowed: List[str] = []
        self.corpus_ref = corpus_ref

    def reset(self, allowed: Sequence[str] = ()) -> None:
        self.calls = self.records = self.bytes = self.out_of_scope = 0
        self.seen = set()
        self.allowed = list(allowed)

    def read(self, corpus: Corpus, path: str, calls: int = 1) -> str:
        """The text of ``path`` read from its source now: one source call (or ``calls``), one record, its bytes."""
        from ..recall.scope_tags import scope_tags_allow
        text = corpus.files[path]
        self.calls += calls
        self.records += 1
        self.bytes += len(text.encode())
        self.seen.add(path)
        if not scope_tags_allow(corpus.meta_of(path).get("scope_tags"), self.allowed):
            self.out_of_scope += 1
        return text

    def outside(self, corpus: Corpus, paths: Sequence[str]) -> int:
        """How many of ``paths`` the request may not see (items an arm returned, which it may not have read)."""
        from ..recall.scope_tags import scope_tags_allow
        return sum(not scope_tags_allow(corpus.meta_of(p).get("scope_tags"), self.allowed) for p in paths)

    def snapshot(self) -> Dict[str, int]:
        return dict(calls=self.calls, records=self.records, bytes=self.bytes, out_of_scope=self.out_of_scope)


class Retriever:
    """The shared machinery: prepare a corpus once (cached by its digest), score a query, answer within a budget. An arm sets ``unit`` and
    overrides ``fit`` (build its index) and ``scores`` (``{unit index: score}`` over the candidates it considers)."""
    unit = "chunk"
    depth = DEPTH

    cache_dir: Optional[str] = None

    def __init__(self) -> None:
        self.corpus: Optional[Corpus] = None
        self.fit_seconds = 0.0
        self.request: Mapping[str, Any] = {}      # the request being answered: timestamp, affinity_tags (focus), scope_tags (see units.ITEM_META)
        self.source = SourceMeter()               # what this arm reads from the sources while answering (0 for an index-only arm)

    def prepare(self, files: Mapping[str, str], history: Sequence[Mapping[str, Any]] = (),
                meta: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Corpus:
        import time
        from .units import digest_of
        if self.corpus is None or self.corpus.digest != digest_of(files, history, self.unit, meta):
            self.corpus = cached_corpus(files, history, self.unit, getattr(self, 'cache_dir', None), meta)
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

    def begin(self, request: Optional[Mapping[str, Any]]) -> None:
        """Note the request's own metadata (time, focus, allowed scope) and zero the source meter, before ranking."""
        self.request = dict(request or {})
        self.source.reset(self.request.get("scope_tags") or ())

    def retrieve(self, query: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = DEFAULT_BUDGET,
                 history: Sequence[Mapping[str, Any]] = (), meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
                 request: Optional[Mapping[str, Any]] = None) -> List[Hit]:
        """The units that answer ``query``, best first, within ``budget_tokens``. An empty list means the arm judged no context is needed.
        ``meta`` (per file) and ``request`` (time, focus, scope) are optional; an arm that does not read them ranks exactly as before."""
        if files is not None:
            self.prepare(files, history, meta)
        self.begin(request)
        if self.corpus is None:
            raise ValueError("retrieve needs files the first time (or prepare(files) beforehand)")
        return within_budget(self.corpus, self.ranking(query), budget_tokens)

    def index_bytes(self) -> int:
        """The size of what this arm keeps beyond the corpus text (postings, vectors), an estimate in bytes."""
        return 0


def query_terms(query: str) -> List[str]:
    return list(dict.fromkeys(tokens(query)))
