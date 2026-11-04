"""A learned reranker: logistic regression over the candidate features, trained on the corpus's own history (each past commit's subject is a
query and the files it changed are the relevant ones). The test cases of the hub are all newer than every commit of the history, so the
split is in time and no test commit is trained on. A consumer with private labels passes them as ``history`` and trains the same way."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from esoi import implementation

from .. import arm_needs as needs
from .fusion import Candidates, FEATURES, HybridRrf
from .base import Retriever
from .units import Corpus

MAX_TRAINING_QUERIES = 400
RECENT = FEATURES.index("recent")


@implementation("retrieve-context", "learned_rerank")
class LearnedRerank(Retriever):
    """The top 100 of the hybrid (and the neighbours of its best hits) reranked by a logistic regression trained on past commits. Recency
    is not learned (a past commit's own recency would leak its label), so its weight is zero."""
    REQUIRES = (needs.FASTEMBED_LOCAL, needs.FASTEMBED_MODEL, needs.NUMPY, needs.SKLEARN)

    def __init__(self, cache_dir: Optional[str] = None, hybrid: Any = None, regularisation: float = 1.0) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.hybrid = hybrid or HybridRrf(cache_dir=cache_dir)
        self.regularisation = regularisation
        self.trained_on = 0

    def fit(self, corpus: Corpus) -> None:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        self.hybrid.adopt(corpus)
        rows: List[List[float]] = []
        labels: List[int] = []
        queries = 0
        for commit in sorted(corpus.history, key=lambda c: str(c.get("date", "")), reverse=True)[:MAX_TRAINING_QUERIES]:
            wanted = {f for f in commit.get("files", []) if f in corpus.files}
            if len(wanted) < 2 or not str(commit.get("subject", "")).strip():
                continue
            candidates = Candidates(self.hybrid, str(commit["subject"]), corpus, minus=sorted(wanted))
            for i, row in zip(candidates.pool, candidates.matrix):
                rows.append(row[:RECENT] + [0.0] + row[RECENT + 1:])
                labels.append(int(corpus.units[i].file in wanted))
            queries += 1
        self.trained_on = queries
        if queries < 20 or sum(labels) < 20:
            raise ValueError(f"learned_rerank needs a history of at least 20 commits that changed two or more files of the corpus; got {queries}")
        self.model = LogisticRegression(C=self.regularisation, max_iter=2000, class_weight="balanced").fit(np.array(rows), np.array(labels))
        self.coefficients = dict(zip(FEATURES, (round(float(w), 3) for w in self.model.coef_[0])))

    def scores(self, query: str) -> Dict[int, float]:
        import numpy as np
        c = Candidates(self.hybrid, query, self.corpus)
        matrix = np.array([r[:RECENT] + [0.0] + r[RECENT + 1:] for r in c.matrix])
        return dict(zip(c.pool, (float(s) for s in self.model.decision_function(matrix)))) if len(matrix) else {}

    def index_bytes(self) -> int:
        return self.hybrid.index_bytes()
