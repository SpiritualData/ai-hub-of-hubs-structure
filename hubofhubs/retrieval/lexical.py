"""Lexical arms: BM25 over the unit body alone, and BM25F over the three fields (path and descriptor, title, body)."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Dict, List, Mapping, Sequence

from esoi import implementation

from .base import Retriever, query_terms
from .units import Corpus

K1, B = 1.2, 0.75
FIELD_WEIGHTS = {"path": 2.0, "title": 3.0, "body": 1.0}   # fixed by reading, before any arm was scored: a name or path match says more than a word in a body


class FieldIndex:
    """BM25 postings of one field of every unit."""

    def __init__(self, corpus: Corpus, name: str):
        self.postings: Dict[str, List[tuple]] = defaultdict(list)
        lengths = [len(u.fields[name]) for u in corpus.units]
        self.average = max(sum(lengths) / max(len(lengths), 1), 1.0)
        self.lengths = lengths
        for unit in corpus.units:
            for term, count in Counter(unit.fields[name]).items():
                self.postings[term].append((unit.index, count))
        n = len(corpus.units)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def score(self, terms: Sequence[str], weight: float, into: Dict[int, float]) -> None:
        for term in terms:
            for index, count in self.postings.get(term, ()):
                norm = count * (K1 + 1) / (count + K1 * (1 - B + B * self.lengths[index] / self.average))
                into[index] = into.get(index, 0.0) + weight * self.idf[term] * norm

    def size(self) -> int:
        return 8 * sum(len(p) for p in self.postings.values())


class FieldedBm25(Retriever):
    weights: Mapping[str, float] = FIELD_WEIGHTS

    def fit(self, corpus: Corpus) -> None:
        self.indexes = {name: FieldIndex(corpus, name) for name in self.weights}

    def scores(self, query: str) -> Dict[int, float]:
        terms = query_terms(query)
        out: Dict[int, float] = {}
        for name, weight in self.weights.items():
            self.indexes[name].score(terms, weight, out)
        return out

    def index_bytes(self) -> int:
        return sum(i.size() for i in self.indexes.values())


@implementation("retrieve-context", "bm25_body")
class Bm25Body(FieldedBm25):
    """BM25 over each chunk's text alone, with no descriptor, title or path field."""
    REQUIRES = ()
    weights = {"body": 1.0}


@implementation("retrieve-context", "bm25_fielded")
class Bm25Fielded(FieldedBm25):
    """BM25F over chunks: the file's path and generated descriptor, the chunk's own names and docstring, and its text, weighed 2, 3 and 1."""
    REQUIRES = ()


@implementation("retrieve-context", "bm25_whole_files")
class Bm25WholeFiles(FieldedBm25):
    """The same fielded BM25 with whole files as the unit, so a file costs all its tokens: the ablation of cutting at natural boundaries."""
    REQUIRES = ()
    unit = "file"
