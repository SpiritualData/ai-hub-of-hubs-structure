"""Scores a context-assembler arm on a known-item check over an existing, already embedded paper collection (a private stage).

The corpus is a fixed sample of ``SAMPLE`` papers read (never written) from a production Qdrant collection together with the vectors it
already stores, so no document is embedded. The arms see the same corpus: the vector arm searches a local Qdrant folder rebuilt from
the pulled vectors (the embedder handed to the store looks each text up in the pulled vectors; it never calls a model), the BM25 arm
indexes the pulled text (title, blank line, abstract) as one file per paper, hybrid and composite combine the two.

A case is one paper and a query made from it: ``title`` (the paper's title) or ``sentence`` (one sentence of its abstract, chosen with a
fixed seed, which does not contain the title). Pass = that paper is among the first 5 ids the arm ranks. nDCG@10 (one relevant paper,
so 1 / log2(rank + 1) when ranked in the first 10) and recall@10 are returned by ``aggregate`` and recorded in the row's details beside a
hash of the sample's ids (so a reader can tell whether two runs saw the same corpus without any id being published).

Only the 300 queries are embedded, once, with the model that embedded the collection (voyage-3.5-lite, input type query), and the
vectors are cached; each arm that searches vectors is charged the queries' tokens at the model's price. The settings are read from the
environment by the names in ``ENV``; the cache lives in a private temporary folder and holds paper text, so it is never committed and
should be deleted after the run. The repository holds the method and the numbers, never the texts or ids.
"""
import hashlib
import json
import os
import random
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_assembler import score as public  # noqa: E402

SAMPLE = 3000
SEED = 20261031
OFFSET = "40000000-0000-0000-0000-000000000000"   # the sample starts at the first point id at or after this one
QUERY_MODEL = "voyage-3.5-lite"
PRICE_PER_MILLION = 0.02   # USD per million tokens, Voyage pricing page, read 2026-10-31
PASS_AT = public.PASS_AT
HITS = public.HITS
THREADS = public.THREADS
CACHE = Path(tempfile.gettempdir()) / "hubofhubs_private_papers"
ENV = dict(url=("QDRANT_READONLY_URL", "QDRANT_URL"), key=("QDRANT_READONLY_API_KEY", "QDRANT_API_KEY"),
           collection=("QDRANT_COLLECTION_RESEARCH_PAPERS",), voyage=("VOYAGE_API_KEY",))


def setting(name):
    value = next((os.environ[n] for n in ENV[name] if os.environ.get(n)), "")
    if not value:
        raise RuntimeError(f"not measured: {' or '.join(ENV[name])} is not set")
    return value


def usable(payload):
    title, abstract = (payload.get("title") or "").strip(), (payload.get("abstract") or "").strip()
    return len(title) >= 20 and len(abstract) >= 300


def pull():
    """The fixed sample: the first ``SAMPLE`` usable points (title of 20+ characters, abstract of 300+, a title not seen before) at or
    after ``OFFSET`` in point-id order, with their stored vectors. Read only. Cached as JSON lines in the private folder."""
    CACHE.mkdir(mode=0o700, exist_ok=True)
    cached = CACHE / "sample.jsonl"
    if not cached.is_file():
        from qdrant_client import QdrantClient
        client = QdrantClient(url=setting("url"), api_key=setting("key"), timeout=120)
        collection, seen, found, offset = setting("collection"), set(), [], OFFSET
        while len(found) < SAMPLE:
            points, offset = client.scroll(collection, limit=256, offset=offset, with_payload=["title", "abstract"], with_vectors=True)
            for point in points:
                payload = point.payload or {}
                title = (payload.get("title") or "").strip().lower()
                if usable(payload) and title not in seen and len(found) < SAMPLE:
                    seen.add(title)
                    found.append(dict(id=str(point.id), title=payload["title"].strip(), abstract=payload["abstract"].strip(),
                                      vector=list(point.vector)))
            if offset is None:
                break
        if len(found) < SAMPLE:
            raise RuntimeError(f"the collection gave only {len(found)} usable points")
        temporary = cached.with_suffix(".tmp")
        temporary.write_text("\n".join(json.dumps(p) for p in found), encoding="utf-8")
        temporary.replace(cached)
    return [json.loads(line) for line in cached.read_text(encoding="utf-8").splitlines()]


def text_of(paper):
    return f"{paper['title']}\n\n{paper['abstract']}"


def sentence_of(paper, index):
    """One sentence of the abstract (60 to 400 characters) picked with a seed from the case's position; the title is not part of it."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paper["abstract"]) if 60 <= len(s.strip()) <= 400]
    sentences = [s for s in sentences if paper["title"].lower() not in s.lower()] or [paper["abstract"][:300]]
    return random.Random(SEED + index).choice(sentences)


def query_of(case, papers):
    paper = papers[case["position"]]
    return paper["title"] if case["kind"] == "title" else sentence_of(paper, case["position"])


def query_vectors(queries):
    """Embed each distinct query once with the collection's own model and cache it. Returns ({query: vector}, tokens used by the set)."""
    cached = CACHE / "queries.json"
    store = json.loads(cached.read_text(encoding="utf-8")) if cached.is_file() else dict(tokens=0, vectors={})
    missing = [q for q in dict.fromkeys(queries) if q not in store["vectors"]]
    if missing:
        import voyageai
        client = voyageai.Client(api_key=setting("voyage"), max_retries=3)
        for start in range(0, len(missing), 64):
            chunk = missing[start:start + 64]
            result = client.embed(chunk, model=QUERY_MODEL, input_type="query")
            store["tokens"] += result.total_tokens
            store["vectors"].update(zip(chunk, result.embeddings))
        cached.write_text(json.dumps(store), encoding="utf-8")
    return store["vectors"], store["tokens"]


def load_cases():
    return json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))


def sample_digest(papers):
    return hashlib.sha256("\n".join(sorted(p["id"] for p in papers)).encode()).hexdigest()[:8]


def adapt(implementation, meter):
    papers = pull()
    vectors, tokens = query_vectors([query_of(c, papers) for c in load_cases()])
    arm = implementation.__name__
    uses_vectors = arm != "BM25ContentStore"
    if uses_vectors:   # every arm that searches vectors is charged the queries' embedding
        meter.model = QUERY_MODEL
        meter.tokens_in += tokens
        meter.cost_usd += tokens * PRICE_PER_MILLION / 1_000_000
        meter.record(max(1, -(-len(vectors) // 64)))
    work = Path(tempfile.mkdtemp(prefix="run-", dir=CACHE))
    docs = work / "docs"
    docs.mkdir()
    for number, paper in enumerate(papers):
        (docs / f"d{number:04d}.txt").write_text(text_of(paper), encoding="utf-8")
    by_text = {text_of(p): p["vector"] for p in papers}
    from hubofhubs.recall.bm25_store import BM25ContentStore
    from hubofhubs.recall.qdrant_store import QdrantVectorStore
    from hubofhubs.recall.vector_assembler import VectorContextAssembler

    def bm25():
        return BM25ContentStore(root=str(docs), top_k=HITS, max_in_view=HITS)

    def vector():
        # The store's embedder is a lookup: documents take the vectors the collection already holds, queries the cached query vectors.
        store = QdrantVectorStore(path=str(work / "qdrant"), vector_size=len(papers[0]["vector"]), embed_max_chars=10 ** 9,
                                  embedder=lambda texts: [by_text[t] for t in texts],
                                  query_embedder=lambda texts: [vectors[t] for t in texts], embedder_id=f"stored:{QUERY_MODEL}")
        store.upsert([dict(id=f"d{n:04d}", text=text_of(p)) for n, p in enumerate(papers)])
        return VectorContextAssembler(store, top_k=HITS, max_in_view=HITS)

    if arm == "BM25ContentStore":
        assembler = bm25()
    elif arm == "VectorContextAssembler":
        assembler = vector()
    elif arm == "HybridContextAssembler":
        assembler = implementation(bm25(), vector())
    elif arm == "CompositeContextAssembler":
        assembler = implementation([bm25(), vector()])
    else:
        raise RuntimeError(f"no wiring for {arm}")
    first = query_of(load_cases()[0], papers)
    assembler.assemble(first)   # builds the BM25 index before any case is timed
    adapt.digest = sample_digest(papers)

    def run(case):
        return public.ranked_ids(arm, assembler.assemble(query_of(case, papers)))[:HITS], f"d{case['position']:04d}"
    return run


def score_case(fn, case):
    ranked, target = fn(case)
    relevant = {target: 1}
    ok = target in ranked[:PASS_AT]
    rank = ranked.index(target) + 1 if target in ranked else 0
    return dict(ok=ok, got=f"known paper at {rank or 'none'}", ndcg=public.ndcg_at(ranked, relevant), recall=public.recall_at(ranked, relevant),
                note="" if ok else f"{case['kind']} query: not in the top {PASS_AT}")


def aggregate(rows):
    return {"ndcg_at_10": round(statistics.mean(r["ndcg"] for r in rows), 4), "recall_at_10": round(statistics.mean(r["recall"] for r in rows), 4),
            "sample_sha": getattr(adapt, "digest", "")}
