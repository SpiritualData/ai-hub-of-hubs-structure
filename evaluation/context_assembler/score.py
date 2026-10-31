"""Scores a context-assembler arm on retrieval: BEIR NFCorpus (test split), the whole corpus, graded relevance.

The cases are the 323 test queries with their judged documents (``cases.json``: ids and grades only). The corpus (3,633 abstracts)
and the query texts are downloaded from the official BEIR URL on first use, checked against ``ZIP_SHA256`` and cached in the system
temporary folder. Each arm gets the same corpus, one file per document (``<id>.txt``: title, blank line, abstract) for the BM25 arm
and the same text as one vector point per document for the vector arm; no model provider is wired (no query rewriting, no review,
no consolidation), so a run makes no model call and costs $0.

Pass = at least one relevant document (grade 1 or 2) in the first 5 ids the arm ranks. Also computed per query and averaged by
``aggregate``: nDCG@10 (gain = grade, discount log2(rank + 1), as trec_eval ``ndcg_cut_10`` that BEIR reports) and recall@10.

The rank of an arm's answer is read from the field that carries it: ``card_ids`` order for bm25 (score order), hybrid (reciprocal
rank fusion) and composite (the members' lists in order), and ``card_metadata[*].effective_score`` for vector, whose ``card_ids`` are
sorted by id on purpose (the arm documents that its list order is not a ranking). Every arm is built with 10 hits so that
nDCG@10 and recall@10 are defined.
"""
import hashlib
import io
import json
import math
import statistics
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/nfcorpus.zip"
ZIP_SHA256 = "efe5be03f8c5b86a5870102d0599d227c8c6e2484328e68c6522560385671b0b"
CACHE = Path(tempfile.gettempdir()) / "hubofhubs_beir_nfcorpus"
PASS_AT = 5
HITS = 10
THREADS = 4   # the embedder's ONNX threads, so a run leaves the machine's other jobs their cores


def dataset():
    """The corpus (id to text), queries (id to text) and test qrels (tab-separated text) of NFCorpus, fetched once and verified."""
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / "nfcorpus.zip"
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != ZIP_SHA256:
        data = urllib.request.urlopen(URL, timeout=120).read()
        if hashlib.sha256(data).hexdigest() != ZIP_SHA256:
            raise RuntimeError(f"{URL} no longer matches sha256 {ZIP_SHA256}; the cases were built from the earlier file")
        archive.write_bytes(data)
    with zipfile.ZipFile(archive) as zf:
        def lines(name):
            return [json.loads(line) for line in zf.read(f"nfcorpus/{name}").decode("utf-8").splitlines() if line.strip()]
        corpus = {d["_id"]: (d.get("title", "").strip() + "\n\n" + d.get("text", "").strip()).strip() for d in lines("corpus.jsonl")}
        queries = {q["_id"]: q["text"] for q in lines("queries.jsonl")}
        qrels = zf.read("nfcorpus/qrels/test.tsv").decode("utf-8")
    return dict(corpus=corpus, queries=queries, qrels=qrels)


def load_cases():
    return json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))


def ndcg_at(ranked, relevant, k=HITS):
    dcg = sum(relevant.get(doc, 0) / math.log2(i + 2) for i, doc in enumerate(ranked[:k]))
    ideal = sorted(relevant.values(), reverse=True)[:k]
    best = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / best if best else 0.0


def recall_at(ranked, relevant, k=HITS):
    return len(set(ranked[:k]) & set(relevant)) / len(relevant) if relevant else 0.0


def ranked_ids(arm, result):
    """The document ids the arm answered with, best first, each once (a ``.txt`` suffix from the BM25 arm's file paths removed)."""
    if arm == "VectorContextAssembler":
        ordered = sorted(result.card_metadata or [], key=lambda m: -float(m.get("effective_score") or 0))
        ids = [m["id"] for m in ordered]
    else:
        ids = list(result.card_ids or [])
    return list(dict.fromkeys(i.removesuffix(".txt") for i in ids))


def build_store(corpus):
    """Write the corpus as files for the BM25 arm and embed it once into a local Qdrant folder for the vector arm (cached by
    corpus size, so only the first vector run pays for embedding). Returns (folder of files, Qdrant folder, seconds to embed)."""
    docs = CACHE / "docs"
    if not docs.is_dir() or len(list(docs.glob("*.txt"))) != len(corpus):
        docs.mkdir(exist_ok=True)
        for doc_id, text in corpus.items():
            (docs / f"{doc_id}.txt").write_text(text, encoding="utf-8")
    return docs, CACHE / "qdrant"


def vector_store(corpus, folder):
    from fastembed import TextEmbedding
    from hubofhubs.recall.embedders import FASTEMBED_EMBEDDER_ID, FASTEMBED_MODEL_NAME
    from hubofhubs.recall.qdrant_store import QdrantVectorStore

    model = TextEmbedding(model_name=FASTEMBED_MODEL_NAME, threads=THREADS)
    store = QdrantVectorStore(path=str(folder), embedder=lambda texts: [list(v) for v in model.embed(texts)],
                              embedder_id=FASTEMBED_EMBEDDER_ID)
    if store.count() != len(corpus):
        started = time.time()
        store.upsert([dict(id=doc_id, text=text) for doc_id, text in corpus.items()])
        print(f"embedded {len(corpus)} documents in {time.time() - started:.0f}s with {FASTEMBED_MODEL_NAME}")
    return store


def adapt(implementation, meter):
    """Build the arm over the corpus; the returned function takes a query id and returns the ranked document ids."""
    data = dataset()
    corpus, queries = data["corpus"], data["queries"]
    docs, qdrant = build_store(corpus)
    arm = getattr(implementation, "func", implementation).__name__   # a variant (name@key=value) arrives as a partial
    from hubofhubs.recall.bm25_store import BM25ContentStore
    from hubofhubs.recall.vector_assembler import VectorContextAssembler

    def bm25():
        return BM25ContentStore(root=str(docs), top_k=HITS, max_in_view=HITS)

    def vector():
        return VectorContextAssembler(vector_store(corpus, qdrant), top_k=HITS, max_in_view=HITS)

    if arm == "BM25ContentStore":
        assembler = implementation(root=str(docs), top_k=HITS, max_in_view=HITS)
    elif arm == "VectorContextAssembler":
        assembler = vector()
    elif arm == "HybridContextAssembler":
        assembler = implementation(bm25(), vector())
    elif arm == "CompositeContextAssembler":
        assembler = implementation([bm25(), vector()])
    else:
        raise RuntimeError(f"no wiring for {arm}")
    assembler.assemble("warm up the index")   # the BM25 index is built lazily: build it before any case is timed
    return lambda query_id: ranked_ids(arm, assembler.assemble(queries[query_id]))[:HITS]


def score_case(fn, case):
    ranked = fn(case["id"])
    relevant = case["relevant"]
    ok = any(doc in relevant for doc in ranked[:PASS_AT])
    first = next((i + 1 for i, doc in enumerate(ranked) if doc in relevant), 0)
    return dict(ok=ok, got=f"first relevant at {first or 'none'}", ndcg=ndcg_at(ranked, relevant), recall=recall_at(ranked, relevant),
                note="" if ok else f"{len(ranked)} returned, none relevant in the top {PASS_AT}")


def aggregate(rows):
    """The headline the harness records as the row's ``details``: the two secondary numbers, to four places."""
    return {"ndcg_at_10": round(statistics.mean(r["ndcg"] for r in rows), 4),
            "recall_at_10": round(statistics.mean(r["recall"] for r in rows), 4)}
