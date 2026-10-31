"""The turn's context cache shares one assembly between the turn start and later reads; the emitter routes events safely."""
import threading
from concurrent.futures import Future

import pytest

from hubofhubs.orchestrate.turn import Emitter, TurnCardCache
from hubofhubs.ports.deep import ProgressEvent
from hubofhubs.ports.events import EVENT_STATUS, Mode


class Assembled:
    def __init__(self, label, partial=False):
        self.label, self.partial = label, partial


class Assembler:
    def __init__(self):
        self.calls = []

    def assemble(self, query, meta=None):
        self.calls.append(query)
        return Assembled(f"fresh:{query}")


def done(value):
    future = Future()
    future.set_result(value)
    return future


def test_a_fresh_assemble_is_cached_so_a_repeat_is_free():
    assembler = Assembler()
    cache = TurnCardCache(assembler, meta=None)
    first, origin = cache.assemble_for_query("q", 1.0)
    again, origin2 = cache.assemble_for_query("q", 1.0)
    cache.close()
    assert (origin, origin2) == ("fresh", "cache") and first is again and assembler.calls == ["q"]


def test_a_registered_prefetch_is_served_and_then_cached():
    cache = TurnCardCache(Assembler(), meta=None)
    cache.register_prefetch("q", done(Assembled("early")))
    got, origin = cache.assemble_for_query("q", 1.0)
    assert origin == "prefetch" and got.label == "early"
    assert cache.assemble_for_query("q", 1.0)[1] == "cache"
    cache.close()


def test_a_partial_result_is_served_but_never_cached():
    assembler = Assembler()
    cache = TurnCardCache(assembler, meta=None)
    cache.register_prefetch("q", done(Assembled("partial", partial=True)))
    assert cache.assemble_for_query("q", 1.0)[0].label == "partial"
    assert cache.assemble_for_query("q", 1.0)[1] == "fresh" and assembler.calls == ["q"]
    cache.close()


def test_no_assembler_means_nothing_and_a_late_prefetch_times_out_but_stays_referenced():
    assert TurnCardCache(None, None).assemble_for_query("q", 0.1) == (None, "none")
    cache = TurnCardCache(Assembler(), meta=None)
    late = Future()
    cache.register_prefetch("q", late)
    with pytest.raises(TimeoutError):
        cache.assemble_for_query("q", 0.01)
    late.set_result(Assembled("late"))
    assert cache.assemble_for_query("q", 1.0)[0].label == "late"
    cache.close()


def test_turn_start_context_reuses_joins_or_reports_pending():
    cache = TurnCardCache(Assembler(), meta=None)
    assert cache.turn_start_context(0.1) == (None, "")
    pending = Future()
    cache.register_prefetch("q", pending)
    assert cache.turn_start_context(0.0) == (None, "pending")
    pending.set_result(Assembled("landed"))
    got, origin = cache.turn_start_context(1.0)
    assert origin == "joined" and got.label == "landed"
    assert cache.turn_start_context(1.0)[1] == "reused"
    cache.close()


def test_discard_prefetch_makes_the_next_read_fresh():
    assembler = Assembler()
    cache = TurnCardCache(assembler, meta=None)
    cache.register_prefetch("q", done(Assembled("partial", partial=True)))
    cache.discard_prefetch("q")
    assert cache.assemble_for_query("q", 1.0)[1] == "fresh"
    cache.close()


def test_render_card_dispatches_to_an_assembler_that_offers_it():
    class Rendering(Assembler):
        def render_card(self, card_id, meta=None):
            return f"card {card_id}"

    cache = TurnCardCache(Rendering(), meta=None)
    assert cache.render_card("c1", 1.0) == ("card c1", "card")
    assert TurnCardCache(Assembler(), None).render_card("c1", 1.0) == (None, "unsupported")
    assert TurnCardCache(None, None).render_card("c1", 1.0) == (None, "none")
    cache.close()


class Sink:
    def __init__(self, fail=False):
        self.seen, self.fail = [], fail

    def update(self, event, mode):
        if self.fail:
            raise RuntimeError("sink down")
        self.seen.append((event.type, mode))


def test_the_emitter_forwards_status_to_the_callback_and_the_sink_and_survives_failures():
    said, sink = [], Sink()
    emitter = Emitter(sink, Mode.LIVE, said.append)
    emitter.status("working")
    assert said == ["working"] and sink.seen == [(EVENT_STATUS, Mode.LIVE)]
    Emitter(Sink(fail=True), Mode.LIVE, lambda t: 1 / 0).status("x")
    Emitter(None, Mode.LIVE, said.append).emit(ProgressEvent(type=EVENT_STATUS, text="t"))


def test_a_detach_request_switches_to_the_background_mode_once():
    detached, flag = [], threading.Event()
    sink = Sink()
    emitter = Emitter(sink, Mode.LIVE, lambda t: None, detach_check=flag.is_set, on_detach=lambda: detached.append(1))
    emitter.emit(ProgressEvent(type=EVENT_STATUS, text="a"))
    flag.set()
    emitter.emit(ProgressEvent(type=EVENT_STATUS, text="b"))
    emitter.emit(ProgressEvent(type=EVENT_STATUS, text="c"))
    assert [m for _, m in sink.seen] == [Mode.LIVE, Mode.BACKGROUND, Mode.BACKGROUND] and detached == [1]
