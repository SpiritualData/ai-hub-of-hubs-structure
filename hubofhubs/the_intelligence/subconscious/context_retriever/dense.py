"""Dense arms: unit vectors from a local embedding model (cached on disk, one vector per distinct text), cosine ranking, and the latent
semantic index (TF-IDF and a truncated SVD), which needs no model at all."""
from __future__ import annotations

import hashlib
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from esoi import implementation

from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_intelligence.subconscious.context_retriever.base import Retriever
from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
from hubofhubs.the_intelligence.subconscious.context_retriever.units import CACHE_FOLDER, Corpus

MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBED_CHARS = 900        # the part of a unit that is embedded (about 225 tokens), so a cold build stays minutes and not an hour
THREADS = 4


def text_key(model: str, text: str) -> str:
    return hashlib.sha256((model + "\0" + text).encode()).hexdigest()[:20]


class VectorCache:
    """One float32 vector per distinct text, kept in one ``.npz`` file; a rerun embeds only the texts it has not seen."""

    def __init__(self, folder: Optional[str], model: str):
        import numpy as np
        self.np = np
        self.model = model
        folder = folder or private_directory(CACHE_FOLDER) or tempfile.mkdtemp(prefix=f"{CACHE_FOLDER}-")   # never a folder another account may write
        self.path = Path(folder) / f"vectors_{model.replace('/', '_')}.npz"
        self.vectors: Dict[str, Any] = {}
        self.dirty = False
        if self.path.is_file():
            with np.load(self.path) as data:
                self.vectors = dict(zip(data["keys"].tolist(), data["vecs"]))

    def save(self) -> None:
        if self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            keys = list(self.vectors)
            self.np.savez(self.path, keys=self.np.array(keys), vecs=self.np.stack([self.vectors[k] for k in keys]))
            self.dirty = False


def load_model(name: str):
    from fastembed import TextEmbedding
    try:
        return TextEmbedding(model_name=name, threads=THREADS, local_files_only=True)
    except Exception:  # noqa: BLE001  the model is not cached here: let fastembed fetch it (an online run) or fail with its own message
        return TextEmbedding(model_name=name, threads=THREADS)


@implementation("context-retriever", "dense_bge_small")
class DenseBgeSmall(Retriever):
    """Cosine over bge-small vectors of the chunks' first 900 characters (title line first), the model run locally through fastembed."""
    REQUIRES = (needs.FASTEMBED_LOCAL, needs.FASTEMBED_MODEL, needs.NUMPY)

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.model: Any = None
        self.cache: Optional[VectorCache] = None
        self.cold_seconds = 0.0

    def embed(self, texts: List[str], prefix: str = "") -> Any:
        np = self.cache.np
        keys = [text_key(MODEL, prefix + t) for t in texts]
        missing = [(k, t) for k, t in dict.fromkeys(zip(keys, texts)) if k not in self.cache.vectors]
        if missing:
            self.model = self.model or load_model(MODEL)
            started = time.time()
            for (k, _), v in zip(missing, self.model.embed([prefix + t for _, t in missing], batch_size=32)):
                self.cache.vectors[k] = np.asarray(v, dtype="float32")
            self.cold_seconds += time.time() - started
            self.cache.dirty = True
        return np.stack([self.cache.vectors[k] for k in keys])

    def unit_text(self, unit) -> str:
        return (f"{unit.file}: {unit.title}\n{unit.text}" if unit.title else f"{unit.file}\n{unit.text}")[:EMBED_CHARS]

    def fit(self, corpus: Corpus) -> None:
        self.cache = self.cache or VectorCache(self.cache_dir, MODEL)
        self.matrix = self.embed([self.unit_text(u) for u in corpus.units])
        self.cache.save()

    def scores(self, query: str) -> Dict[int, float]:
        q = self.embed([query], QUERY_PREFIX)[0]
        sims = self.matrix @ q
        top = self.cache.np.argsort(-sims)[:self.depth * 2]
        return {int(i): float(sims[i]) for i in top}

    def index_bytes(self) -> int:
        return int(self.matrix.nbytes)


@implementation("context-retriever", "lsi")
class LatentSemantic(Retriever):
    """TF-IDF over chunk text projected to 128 latent dimensions by a truncated SVD (LSI), cosine in the latent space: free, no model."""
    REQUIRES = (needs.SKLEARN,)
    dimensions = 128

    def fit(self, corpus: Corpus) -> None:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
        docs = [" ".join(u.fields["title"] + u.fields["body"]) for u in corpus.units]
        self.vectorizer = TfidfVectorizer(analyzer=str.split, sublinear_tf=True, min_df=2)
        tfidf = self.vectorizer.fit_transform(docs)
        self.svd = TruncatedSVD(n_components=min(self.dimensions, tfidf.shape[1] - 1), random_state=0)
        self.matrix = normalize(self.svd.fit_transform(tfidf))

    def scores(self, query: str) -> Dict[int, float]:
        from sklearn.preprocessing import normalize
        from hubofhubs.the_intelligence.subconscious.context_retriever.units import tokens
        q = normalize(self.svd.transform(self.vectorizer.transform([" ".join(tokens(query))])))
        sims = (self.matrix @ q[0])
        import numpy as np
        top = np.argsort(-sims)[:self.depth * 2]
        return {int(i): float(sims[i]) for i in top}

    def index_bytes(self) -> int:
        return int(self.matrix.nbytes + 16 * len(self.vectorizer.vocabulary_))
