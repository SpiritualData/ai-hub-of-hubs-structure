"""affinity_tags: the soft sibling of scope_tags. It reorders visible items, never hides one, and is inert by default."""
from hubofhubs.ports.context import VectorHit
from hubofhubs.recall.affinity_tags import affinity_factor, affinity_label, affinity_tags_of
from hubofhubs.recall.record_assembler import RecordContextAssembler, rank_records
from hubofhubs.recall.vector_assembler import VectorContextAssembler
from tests.test_recall_vector_assembler import FakeStore, hit


def test_factor_is_neutral_without_tags_and_boosts_home_and_discounts_away():
    kw = dict(home_boost=1.5, away_factor=0.5)
    assert affinity_factor(None, ["p:1"], **kw) == 1.0 and affinity_factor(["p:1"], None, **kw) == 1.0
    assert affinity_factor(["p:1", "p:2"], ["p:2"], **kw) == 1.5
    assert affinity_factor(["p:1"], ["p:2"], **kw) == 0.5
    assert affinity_factor(["p:1"], ["p:2"]) == 1.0          # defaults: no effect
    assert affinity_factor(["p:1"], ["p:2"], home_boost="x", away_factor=None) == 1.0   # never raises


def test_label_and_item_accessor_never_raise():
    assert affinity_label(["a:1", "b:2"]) == "a:1, b:2" and affinity_label(None) == ""
    assert affinity_tags_of({"affinity_tags": "a:1"}) == ["a:1"] and affinity_tags_of(None) == []


def test_vector_default_is_bit_for_bit_and_weights_reorder_without_hiding():
    hits = [hit("a-away", 0.9, affinity_tags=["p:2"]), hit("b-home", 0.8, affinity_tags=["p:1"])]
    meta = {"affinity_tags": ["p:1"]}

    def run(**kw):
        return VectorContextAssembler(FakeStore(hits), max_in_view=1, num_queries=0, **kw).assemble("words", meta=meta)

    plain = VectorContextAssembler(FakeStore(hits), max_in_view=1, num_queries=0).assemble("words")
    assert run().card_ids == plain.card_ids == ["a-away"]
    assert [m["effective_score"] for m in run().card_metadata] == [m["effective_score"] for m in plain.card_metadata]
    assert run(affinity_home_boost=1.5).card_ids == ["b-home"]
    assert run(affinity_away_factor=0.5).card_ids == ["b-home"]
    both = VectorContextAssembler(FakeStore(hits), max_in_view=5, num_queries=0, affinity_away_factor=0.1).assemble("words", meta=meta)
    assert sorted(both.card_ids) == ["a-away", "b-home"]          # away is never hidden
    assert both.card_metadata[0]["affinity_tags"] in (["p:2"], ["p:1"])


def test_scope_fence_still_hides_while_affinity_does_not():
    store = FakeStore([hit("x", 0.9, scope_tags=["t:2"], affinity_tags=["p:1"])])
    ctx = VectorContextAssembler(store, num_queries=0, affinity_home_boost=2).assemble(
        "words", meta={"scope_tags": ["t:1"], "affinity_tags": ["p:1"]})
    assert ctx.card_ids == []


def test_record_ranking_orders_by_affinity_after_the_floor():
    rows = [{"id": "away", "text": "dana teaches tuesday", "affinity_tags": ["q:2"]},
            {"id": "home", "text": "dana teaches tuesday", "affinity_tags": ["q:1"]}]
    base = rank_records("dana tuesday", rows)
    assert [r["id"] for _, r in base] == ["away", "home"]
    best = rank_records("dana tuesday", rows, turn_affinity_tags=["q:1"], home_boost=2.0)
    assert [r["id"] for _, r in best] == ["home", "away"]
    assert rank_records("dana tuesday", rows, turn_affinity_tags=["q:1"], away_factor=0.0, min_score=0.1)[0][1]["id"] == "home"
    out = RecordContextAssembler(lambda m: rows, max_records=1, affinity_home_boost=2.0).assemble(
        "dana tuesday", meta={"affinity_tags": ["q:1"]})
    assert out.card_ids == ["home"]


def test_a_hit_from_another_grouping_says_so_in_its_rendered_block():
    store = FakeStore([hit("away", 0.9, affinity_tags=["p:2"]), hit("home", 0.9, affinity_tags=["p:1"]), hit("plain", 0.9)])
    ctx = VectorContextAssembler(store, num_queries=0).assemble("words", meta={"affinity_tags": ["p:1"]})
    sections = {m["id"]: m["rendered_section"] for m in ctx.card_metadata}
    assert "from another grouping: p:2" in sections["away"]
    assert "another grouping" not in sections["home"] + sections["plain"]
