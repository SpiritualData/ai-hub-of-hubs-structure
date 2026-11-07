"""Offline tests for the cheap-first context path: a turn that already holds a context tops up with search and score only,
escalates to the full assembly when the cheap result is not decisive, and two arms asking the same question share one model call."""
from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from hubofhubs.api import VectorHit
from hubofhubs.the_body.internal_context.interface import AssembledContext
from hubofhubs.the_intelligence.mind.delegation.overseer.turn import TurnCardCache
from hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.vector_assembler import VectorContextAssembler
from hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.card_selection import (
    cheap_result_is_decisive, retrieve_only, with_retrieve_depth)


class ScriptedAssembler:
    """Records each call's depth and answers with the next scripted result for that depth."""

    def __init__(self, cheap: AssembledContext, full: AssembledContext):
        self.cheap, self.full = cheap, full
        self.calls: List[str] = []

    def assemble(self, task_text: str, *, meta: Optional[Dict[str, Any]] = None) -> AssembledContext:
        depth = "retrieve" if retrieve_only(meta) else "full"
        self.calls.append(depth)
        return self.cheap if depth == "retrieve" else self.full


def strong(view: str = "context") -> AssembledContext:
    return AssembledContext(context_view=view, card_metadata=[{"id": "a", "relevance_score": 0.8}])


def weak() -> AssembledContext:
    return AssembledContext(context_view="thin", card_metadata=[{"id": "a", "relevance_score": 0.2}])


def test_decisive_is_a_fact_over_scores_not_words():
    assert cheap_result_is_decisive(strong())
    assert not cheap_result_is_decisive(weak())
    assert not cheap_result_is_decisive(AssembledContext())
    assert not cheap_result_is_decisive(None)
    assert cheap_result_is_decisive(AssembledContext(context_view="turns only"))   # no card scores: there is text, nothing to doubt


def test_turn_start_read_is_full_then_followup_is_cheap():
    asm = ScriptedAssembler(cheap=strong("cheap"), full=strong("full"))
    cache = TurnCardCache(asm, {"scope_tags": ["q"]})
    first, _ = cache.assemble_for_query("what is our top priority", 5)
    assert first.context_view == "full" and asm.calls == ["full"]
    second, _ = cache.assemble_for_query("onboarding completion milestone", 5)
    assert second.context_view == "cheap" and asm.calls == ["full", "retrieve"]
    assert cache.cheap_reads == 1 and cache.escalated_reads == 0


def test_followup_escalates_when_the_cheap_result_is_weak_or_empty():
    for cheap in (weak(), AssembledContext()):
        asm = ScriptedAssembler(cheap=cheap, full=strong("full"))
        cache = TurnCardCache(asm, None)
        cache.assemble_for_query("first", 5)
        got, _ = cache.assemble_for_query("second", 5)
        assert got.context_view == "full" and asm.calls == ["full", "retrieve", "full"]
        assert cache.escalated_reads == 1


def test_the_other_arm_keeps_every_read_full():
    asm = ScriptedAssembler(cheap=strong("cheap"), full=strong("full"))
    cache = TurnCardCache(asm, None)
    cache.cheap_followups = False
    cache.assemble_for_query("first", 5)
    cache.assemble_for_query("second", 5)
    assert asm.calls == ["full", "full"]


def test_a_partial_turn_start_with_content_counts_as_context_in_hand_and_an_empty_one_does_not():
    asm = ScriptedAssembler(cheap=strong("cheap"), full=strong("full"))
    cache = TurnCardCache(asm, None)
    cache.note_turn_start_result(AssembledContext(context_view="some context", partial=True))
    cache.assemble_for_query("first", 5)
    assert asm.calls == ["retrieve"]
    asm2 = ScriptedAssembler(cheap=strong("cheap"), full=strong("full"))
    cache2 = TurnCardCache(asm2, None)
    cache2.note_turn_start_result(AssembledContext(partial=True))
    cache2.assemble_for_query("first", 5)
    assert asm2.calls == ["full"]


class CountingProvider:
    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()

    def answer(self, messages, *, model=None, system=None) -> str:
        with self.lock:
            self.calls += 1
        import time
        time.sleep(0.05)
        return "query one\nquery two"

    def list_models(self):
        return ["m"]


class OneHitStore:
    def __init__(self):
        self.queries: List[str] = []

    def search(self, query, *, scope=None, top_k=8):
        self.queries.append(query)
        return [VectorHit(id="c1", score=0.9, text="a card", payload={"paths": ["a.py"]})]

    def upsert(self, items, *, scope=None):
        pass

    def sync(self, items, *, scope=None):
        pass


def test_retrieve_depth_searches_the_raw_task_only():
    provider, store = CountingProvider(), OneHitStore()
    arm = VectorContextAssembler(store, provider=provider, llm_review=True, confidence_min_score=0.0)
    arm.assemble("top priority", meta=with_retrieve_depth(None))
    assert provider.calls == 0 and store.queries == ["top priority"]
    arm.assemble("top priority full")
    assert provider.calls >= 1 and len(store.queries) > 2


def test_two_arms_asking_the_same_question_at_once_share_one_query_generation():
    provider = CountingProvider()
    arms = [VectorContextAssembler(OneHitStore(), provider=provider, llm_review=False, confidence_min_score=0.0) for _ in range(2)]
    threads = [threading.Thread(target=a.assemble, args=("same task text",)) for a in arms]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert provider.calls == 1



def test_a_reference_resolved_a_moment_ago_is_not_fetched_again_until_a_write_clears_it():
    from hubofhubs.api import clear_resolution_memo
    from hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.card_content_render import resolve_remembered

    class Resolver:
        calls = 0

        def resolve(self, locator, *, max_chars):
            Resolver.calls += 1
            return f"data {Resolver.calls}"

    clear_resolution_memo()
    r = Resolver()
    first = resolve_remembered(r, "chat_thread", {"id": "t1"}, 500)
    assert resolve_remembered(r, "chat_thread", {"id": "t1"}, 500) == first and Resolver.calls == 1
    resolve_remembered(r, "chat_thread", {"id": "t2"}, 500)
    assert Resolver.calls == 2                                     # another reference is another fetch
    clear_resolution_memo()
    assert resolve_remembered(r, "chat_thread", {"id": "t1"}, 500) != first and Resolver.calls == 3


def test_a_cards_items_are_fetched_together_and_the_budget_is_applied_in_relevance_order():
    import time as clock
    from hubofhubs.api import clear_resolution_memo, render_card_content_blocks

    class SlowResolver:
        def resolve(self, locator, *, max_chars):
            clock.sleep(0.2)
            return f"text of {locator['id']} " + "x" * 50

    clear_resolution_memo()
    card = {"content": [{"id": f"i{n}", "type": "note", "locator": {"id": f"i{n}"}, "why": "w", "ts": f"2026-11-0{n}"} for n in range(1, 6)]}
    started = clock.monotonic()
    blocks = render_card_content_blocks(card, {"note": SlowResolver()}, task_kws=set(), max_refs=5, max_ref_chars=400)
    assert clock.monotonic() - started < 0.7 and len(blocks) == 5 and all(b["text"].startswith("text of") for b in blocks)
