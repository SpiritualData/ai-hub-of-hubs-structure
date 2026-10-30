"""Read-only access to a mounted store's points on another Qdrant backend, and the embedder factories (settings are arguments)."""
import os
import sys

import pytest

from hubofhubs.ports.context import VectorHit
from hubofhubs.recall import embedders
from hubofhubs.recall.card_vectors import (
    Compatibility,
    ReadOnlyVectorReader,
    RemoteMountReaders,
    compatibility,
    embedded_reason,
    seed_scope_digest,
)
from hubofhubs.recall.qdrant_store import scope_hash
from hubofhubs.recall.vector_scopes import CARD_SEED_SCOPE


class Point:
    def __init__(self, id, score, payload):
        self.id, self.score, self.payload = id, score, payload


class RecordingClient:
    """Records every call it receives; knows one collection of 3-dimensional vectors."""

    def __init__(self):
        self.calls = []

    def collection_exists(self, name):
        self.calls.append(("collection_exists", name))
        return name == "own_default_3"

    def get_collection(self, collection_name):
        self.calls.append(("get_collection", collection_name))
        raise RuntimeError("unknown")

    def query_points(self, **kwargs):
        self.calls.append(("query_points", kwargs["collection_name"]))
        self.filter = kwargs["query_filter"]
        points = [Point(7, 0.9, {"_text": "a card", "_id": "card:1", "_scope": "x", "store_id": "s1", "paths": ["a.py"]})]
        return type("Response", (), {"points": points})()


def test_the_reader_has_no_write_method_and_makes_only_read_calls():
    names = {n for n in dir(ReadOnlyVectorReader) if not n.startswith("__")}
    assert not names & {"upsert", "delete", "set_payload", "create_collection", "sync"}
    client = RecordingClient()
    reader = ReadOnlyVectorReader(client, collection_prefix="own", seed_scope={"own_point_class": "card_seed"})
    hits = reader.query([0.1, 0.2, 0.3], "s1", top_k=4)
    assert hits == [VectorHit(id="card:1", score=0.9, text="a card", payload={"store_id": "s1", "paths": ["a.py"]})]
    assert {call[0] for call in client.calls} <= {"collection_exists", "get_collection", "query_points"}


def test_the_seeded_partition_digest_follows_the_consumers_scope():
    mine = {"own_point_class": "card_seed"}
    assert seed_scope_digest(mine) == scope_hash(mine) != seed_scope_digest()
    assert seed_scope_digest() == scope_hash(CARD_SEED_SCOPE)
    client = RecordingClient()
    ReadOnlyVectorReader(client, collection_prefix="own", seed_scope=mine).query([0.1, 0.2, 0.3], "s1")
    assert scope_hash(mine) in repr(client.filter) and scope_hash(CARD_SEED_SCOPE) not in repr(client.filter)


def test_compatibility_needs_the_same_dimension_and_the_same_family_when_both_name_one():
    assert compatibility({"vector_size": 3}, query_dim=3) == Compatibility(True)
    assert not compatibility({"vector_size": 3}, query_dim=4).ok
    assert not compatibility({"vector_size": 3, "embedder": "a"}, query_dim=3, reader_embedder="b").ok
    assert compatibility({"vector_size": 3, "embedder": "a"}, query_dim=3).ok
    assert not compatibility({}, query_dim=None).ok


def test_an_embedded_location_is_never_opened_and_the_remedy_wording_is_the_consumers(tmp_path):
    assert "cannot read" in embedded_reason({"path": str(tmp_path / "missing")}) or os.access(str(tmp_path), os.R_OK)
    assert embedded_reason({}).endswith("publish them on a server")
    assert embedded_reason({}, "run the consumer's command").endswith("run the consumer's command")
    readers = RemoteMountReaders(lambda location, prefix: None)
    assert readers.reader_for("http://example.invalid:6333", "own") is None


def test_the_embedder_ids_and_factories_take_their_settings_as_arguments(monkeypatch):
    monkeypatch.setenv("VOYAGE_MODEL", "from-env")
    monkeypatch.setenv("QAR_EMBEDDER_BACKEND", "voyage")
    assert embedders.voyage_embedder_id() == "voyage:voyage-3-lite"
    assert embedders.openai_embedder_id("m") == "openai:m"
    assert embedders.embedder_id_for("voyage", voyage_model="v") == "voyage:v"
    assert embedders.embedder_id_for("OpenAI") == "openai:text-embedding-3-small"
    assert embedders.embedder_id_for("") == embedders.FASTEMBED_EMBEDDER_ID
    monkeypatch.setitem(sys.modules, "voyageai", None)
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ImportError, match="voyageai"):
        embedders.make_voyage_embedder()
    with pytest.raises(ImportError, match="openai"):
        embedders.make_openai_embedder()
