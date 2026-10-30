"""Seeding a vector store must cost the same on 100 cards and 100,000, and the store's settings are its arguments.

``sync()`` hands every new or changed item to ``upsert``, which on a cold store is the entire corpus. Embedding that in one
call is what OOM-killed a runner mid-task: a transformer's attention tensor is ``batch x heads x seq^2``, and the ONNX arena
serving it grows to the high-water mark. These tests pin the bound (the embedder never sees more than one batch at a time)
without a real model, and pin that no environment variable moves any setting.
"""
from hubofhubs.recall.embedders import EMBED_BATCH_DEFAULT, EMBED_MAX_CHARS_DEFAULT, FASTEMBED_EMBEDDER_ID
from hubofhubs.recall.qdrant_store import QdrantVectorStore, point_id, scope_hash
from hubofhubs.recall.vector_scopes import CARD_SEED_SCOPE, SeedItems


class FakeQdrant:
    def __init__(self):
        self.upserted = []

    def upsert(self, *, collection_name, points):
        self.upserted.extend(points)


def stubbed_store(embed_spy, **settings):
    """A QdrantVectorStore with qdrant and the embedder stubbed out (no server, no model)."""
    store = QdrantVectorStore.__new__(QdrantVectorStore)
    for name, value in settings.items():
        setattr(store, name, value)
    store._client = FakeQdrant()
    store._collection_name = lambda: "c"
    store._ensure_collection = lambda coll: None
    store._adopt_embedding_dim = lambda dim: None
    store._embed = embed_spy
    store._embed_safe = QdrantVectorStore._embed_safe.__get__(store)
    return store


def items_of(n, text="x" * 50):
    return [{"id": f"c{i}", "text": text, "fingerprint": i, "payload": {}} for i in range(n)]


def test_the_embedder_never_sees_more_than_one_batch():
    seen = []

    def embed(texts):
        seen.append(len(texts))
        return [[0.1, 0.2, 0.3] for _ in texts]

    store = stubbed_store(embed, embed_batch_size=16)
    store.upsert(items_of(100))
    assert max(seen) <= 16, f"a batch of {max(seen)} reached the embedder"
    assert sum(seen) == 100                       # every item still embedded, exactly once
    assert len(store._client.upserted) == 100     # and every point still written


def test_every_item_is_written_even_when_the_count_is_not_a_multiple_of_the_batch():
    store = stubbed_store(lambda texts: [[0.0] for _ in texts], embed_batch_size=16)
    store.upsert(items_of(37))                    # 16 + 16 + 5
    assert len(store._client.upserted) == 37
    assert {p.payload["_id"] for p in store._client.upserted} == {f"c{i}" for i in range(37)}


def test_long_text_is_truncated_for_the_embedder_but_kept_whole_in_the_payload():
    embedded = []

    def embed(texts):
        embedded.extend(texts)
        return [[0.0] for _ in texts]

    store = stubbed_store(embed, embed_max_chars=100)
    long_text = "y" * 5000
    store.upsert([{"id": "c1", "text": long_text, "payload": {}}])
    assert len(embedded[0]) == 100
    assert store._client.upserted[0].payload["_text"] == long_text


def test_the_defaults_are_the_measured_ones_and_the_environment_changes_nothing(monkeypatch):
    monkeypatch.setenv("QAR_EMBED_BATCH", "3")
    monkeypatch.setenv("EMBED_BATCH", "3")
    store = QdrantVectorStore.__new__(QdrantVectorStore)
    assert (store.batch_limit(), store.text_limit()) == (EMBED_BATCH_DEFAULT, EMBED_MAX_CHARS_DEFAULT)
    assert EMBED_BATCH_DEFAULT == 16 and FASTEMBED_EMBEDDER_ID == "fastembed:BAAI/bge-small-en-v1.5"


def test_an_embedder_failure_stops_the_upsert_without_raising():
    def embed(texts):
        raise RuntimeError("model unavailable")

    store = stubbed_store(embed, embed_batch_size=16)
    store.upsert(items_of(50))
    assert store._client.upserted == []


def test_the_scope_digest_and_the_point_id_are_stable_functions_of_the_scope_and_the_item():
    # Persisted data is found by these two: a change here silently orphans stored points.
    assert scope_hash(None) is None and scope_hash({}) is None
    assert scope_hash({"a": 1, "b": 2}) == scope_hash({"b": 2, "a": 1})
    assert scope_hash(CARD_SEED_SCOPE) != scope_hash({"qar_point_class": "card_seed"})   # the key is part of the digest
    assert point_id("card:1", None) == point_id("card:1", None)
    assert point_id("card:1", "abc") != point_id("card:1", None)


def test_a_seed_list_remembers_how_many_cards_the_source_holds():
    assert SeedItems([{"id": "a"}], offered=10).offered == 10
    assert SeedItems([{"id": "a"}, {"id": "b"}], offered=1).offered == 2
