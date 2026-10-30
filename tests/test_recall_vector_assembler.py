"""The hub's vector context assembler: gate, ranking, render order, scope fence, seed, record, and the injected prompts.

The consumer's integration tests of the same code (through its binding) stay with the consumer; these pin what the hub
promises on its own, with a fake vector store and a scripted provider and no network.
"""
import logging
import threading

import pytest

from hubofhubs.ports.context import VectorHit, VectorStoreBase
from hubofhubs.recall.vector_assembler import (
    MAX_SEED_ITEMS_DEFAULT,
    VectorContextAssembler,
    VectorPrompts,
    seed_source_takes_limit,
    snippet,
    task_slug,
)
from hubofhubs.recall.vector_scopes import CARD_SEED_SCOPE, SeedItems


class FakeStore(VectorStoreBase):
    def __init__(self, hits=(), held=0):
        self.hits, self.held = list(hits), held
        self.searches, self.upserts, self.syncs, self.evicted = [], [], [], []

    def search(self, query, *, scope=None, top_k=8):
        self.searches.append((query, scope, top_k))
        return list(self.hits)

    def upsert(self, items, *, scope=None):
        self.upserts.append((items, scope))

    def sync(self, items, *, scope=None):
        self.syncs.append((list(items), scope))
        return len(items)

    def count(self, *, scope=None):
        return self.held

    def evict_oldest(self, n, *, scope=None, ts_key="ts"):
        self.evicted.append((n, scope))
        return n


class Provider:
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def answer(self, messages, model=None, **kwargs):
        self.prompts.append(messages[-1]["content"])
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def hit(id, score, text="", **payload):
    return VectorHit(id=id, score=score, text=text or id, payload=payload)


def test_the_confidence_gate_is_on_raw_similarity_and_a_hit_may_declare_its_own_floor():
    store = FakeStore([hit("keep", 0.8), hit("drop", 0.3), hit("own-floor", 0.5, vector_min_score=0.9)])
    ctx = VectorContextAssembler(store, confidence_min_score=0.45, num_queries=0).assemble("alpha beta")
    assert ctx.card_ids == ["keep"]
    assert VectorContextAssembler(FakeStore([hit("only", 0.1)]), confidence_min_score=0.45).assemble("x").card_ids == []


def test_selection_follows_the_score_but_the_render_order_is_stable_by_card_id():
    store = FakeStore([hit("b-card", 0.9), hit("a-card", 0.8), hit("c-card", 0.7)])
    ctx = VectorContextAssembler(store, max_in_view=2, num_queries=0).assemble("topic words")
    assert ctx.card_ids == ["a-card", "b-card"]                      # the two best, listed by id
    by_id = {m["id"]: m for m in ctx.card_metadata}
    assert by_id["b-card"]["effective_score"] > by_id["a-card"]["effective_score"]


def test_a_hit_for_another_scope_tag_is_fenced_out_and_an_untagged_one_stays():
    store = FakeStore([hit("mine", 0.9, scope_tags=["p:1"]), hit("theirs", 0.9, scope_tags=["p:2"]), hit("shared", 0.9)])
    ctx = VectorContextAssembler(store, num_queries=0).assemble("words", meta={"scope_tags": ["p:1"]})
    assert sorted(ctx.card_ids) == ["mine", "shared"]


def test_the_seed_is_written_under_the_consumers_seed_scope_and_capped_with_a_warning(caplog):
    own = {"own_point_class": "card_seed"}
    items = SeedItems([{"id": f"c{i}", "text": "t", "fingerprint": i} for i in range(3)], offered=10)
    store = FakeStore()
    assembler = VectorContextAssembler(store, seed_source=lambda: items, max_seed_items=3, seed_scope=own)
    with caplog.at_level(logging.WARNING):
        assembler.assemble("anything")
    assert store.syncs and store.syncs[0][1] == own and len(store.syncs[0][0]) == 3
    assert "has 10 cards; only the first 3 are searched by meaning" in caplog.text
    plain = FakeStore()
    VectorContextAssembler(plain, seed_source=lambda: [{"id": "a", "text": "t"}]).assemble("anything")
    assert plain.syncs[0][1] == CARD_SEED_SCOPE and MAX_SEED_ITEMS_DEFAULT == 1000


def test_a_seed_source_that_takes_a_limit_is_handed_the_ceiling():
    seen = []

    def source(limit=None):
        seen.append(limit)
        return [{"id": "a", "text": "t"}]

    assert seed_source_takes_limit(source) and not seed_source_takes_limit(lambda: [])
    VectorContextAssembler(FakeStore(), seed_source=source, max_seed_items=5).assemble("x")
    assert seen == [5]


def test_the_seed_can_run_on_a_named_background_thread():
    names, done = [], threading.Event()

    def source():
        names.append(threading.current_thread().name)
        done.set()
        return [{"id": "a", "text": "t"}]

    VectorContextAssembler(FakeStore(), seed_source=source, seed_in_background=True, seed_thread_name="own-seed").start_seed()
    assert done.wait(5) and names == ["own-seed"]


def test_record_upserts_one_association_per_task_and_bounds_the_count():
    store = FakeStore(held=7)
    assembler = VectorContextAssembler(store, max_associations=5, clock=lambda: 1000.0)
    assembler.record("Fix the Poller!", {"files": ["a.py"], "symbols": ["f"], "scope": {"goal": "g"}})
    items, scope = store.upserts[0]
    assert items[0]["id"] == f"assoc:{task_slug('Fix the Poller!')}" == "assoc:fix-the-poller"
    assert items[0]["payload"]["ts"] == 1000.0 and scope == {"goal": "g"}
    assert store.evicted == [(2, {"goal": "g"})]


def test_the_consumers_prompts_are_what_the_model_is_asked_and_a_repeat_costs_no_call():
    store = FakeStore([hit("c1", 0.9), hit("c2", 0.9)])
    provider = Provider("first query\nsecond query", "0")
    prompts = VectorPrompts(queries=lambda n, task: f"Q{n}:{task}", review=lambda task, items: f"R:{task}:{items[:3]}",
                            association=lambda task, region: f"A:{task}:{region}", excerpt=lambda task: task[:5])
    assembler = VectorContextAssembler(store, provider=provider, num_queries=2, prompts=prompts)
    ctx = assembler.assemble("abcdefghij")
    assert provider.prompts[0] == "Q2:abcde" and provider.prompts[1].startswith("R:abcdefghij:[0]")
    assert ctx.card_ids == ["c1"]
    calls = len(provider.prompts)
    assembler.assemble("abcdefghij")
    assert len(provider.prompts) == calls                      # the selection memo: same task, same candidates
    provider.replies = ["one sentence"]
    assembler.record("task text", {"files": ["a.py"]})
    assert provider.prompts[-1] == "A:task text:files: a.py"


def test_the_default_prompts_are_the_standard_texts_with_no_consumer_wording():
    provider = Provider("q one", "none")
    VectorContextAssembler(FakeStore([hit("c1", 0.9)]), provider=provider, num_queries=1).assemble("find the thing")
    assert provider.prompts[0].startswith("Generate 1 short, diverse search queries") and "find the thing" in provider.prompts[0]
    assert "Output ONLY the indices" in provider.prompts[1]


def test_a_snippet_is_capped_even_when_the_text_has_no_newline():
    assert len(snippet("x" * 5000)) <= 400
    assert snippet("a\n\nb\nc\nd") == "a | b | c"


@pytest.mark.parametrize("broken", [RuntimeError("down")])
def test_assemble_never_raises(broken):
    class Broken(FakeStore):
        def search(self, *args, **kwargs):
            raise broken

    assert VectorContextAssembler(Broken(), num_queries=0).assemble("x").card_ids == []


def test_the_retrieval_arms_are_registered_under_the_context_assembler_seat_and_none_is_selected():
    import hubofhubs
    from hubofhubs.recall.vector_assembler import VectorContextAssembler as Arm
    assert {"vector", "bm25", "hybrid", "composite"} <= set(hubofhubs.names("context-assembler"))
    assert hubofhubs.resolve("context-assembler", config=hubofhubs.AssemblyConfig(selections={"context-assembler": "vector"})) is Arm
