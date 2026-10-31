"""Per-turn machinery: the turn's context cache and the run's progress-event router.

Both depend only on the hub's ports. The cache shares one context assembly between the turn start and the mid-loop reads; the
emitter forwards progress events to the sink the run's mode chose and lets a live run drop to the background sink.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import Future, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, Dict, Optional, Tuple

from hubofhubs.ports.deep import ProgressEvent, ProgressSink
from hubofhubs.ports.events import EVENT_STATUS, Mode
from hubofhubs.ports.scope import ScopedThreadPoolExecutor as ThreadPoolExecutor


class TurnCardCache:
    """One in-run, query-keyed cache of context assembly, shared by BOTH context paths this turn.

    Turn-start assembly and mid-loop ``{"cards": <query>}`` reads reach the SAME cards through ONE object, so a 5s
    turn-start timeout is no longer unrecoverable for the whole turn. Two mechanisms:

    * The turn-start eager pre-fetch registers its running ``Future`` here (``register_prefetch``).
      When that fetch TIMES OUT at turn start, the future is kept referenced (not cancelled), so if
      it lands late a later mid-loop read for the SAME query serves it from here WITHOUT re-running
      assembly.
    * A mid-loop read for a query with no pre-fetch runs a fresh, bounded ``assemble`` and caches it
      under the query, so repeats within the turn are free.

    A deep run later in the same turn reuses the turn-start assembly the same way
    (``turn_start_context``) instead of assembling the same request again: a completed one is
    handed over, a still-running or timed-out one is waited for (bounded), never duplicated.

    Everything is best-effort and thread-safe (mid-loop reads run in a parallel pool):
    a lock guards the two dicts. No cross-turn persistence -- the cache dies with the run.
    """

    def __init__(self, assembler: Optional[Any], meta: Optional[Dict[str, Any]]):
        self.assembler = assembler
        self.meta = meta or None
        self.lock = threading.Lock()
        self.results: Dict[str, Any] = {}          # query -> AssembledContext (completed)
        self.futures: Dict[str, Future] = {}       # query -> in-flight assemble (may land late)
        self.executor: Optional[ThreadPoolExecutor] = None
        self.emit: Optional[Any] = None            # per-run event sink (set by run()); may stay None
        self.turn_start_query: Optional[str] = None   # the query the turn-start pre-fetch ran for
        self.turn_start_began: Optional[float] = None   # time.monotonic() when that pre-fetch was registered
        self.turn_start_result: Any = None            # what the turn-start collect used (full or partial)

    def register_prefetch(self, query: str, future: Future) -> None:
        """Register the turn-start eager pre-fetch future under its query. Never raises."""
        if not query or future is None:
            return
        try:
            with self.lock:
                self.futures[query] = future
                self.turn_start_query = query
                self.turn_start_began = time.monotonic()
        except Exception:  # noqa: BLE001
            pass

    def note_turn_start_result(self, assembled: Any) -> None:
        """Remember the assembly the turn-start collect actually used, FULL or the PARTIAL it settled
        for. Unlike ``register_result`` this keeps a partial too, because it answers a different
        question: not "what may a mid-loop read serve" but "what has this turn already paid for".
        Never raises."""
        if assembled is None:
            return
        try:
            with self.lock:
                self.turn_start_result = assembled
        except Exception:  # noqa: BLE001
            pass

    def turn_start_context(self, timeout: float,
                           on_wait: Optional[Callable[[], None]] = None) -> Tuple[Any, str]:
        """This turn's start-of-turn assembly for a caller that would otherwise run the same one
        again, plus a one-word ORIGIN. Never raises and never starts an assembly of its own.

        * ``"reused"``: the turn-start collect already holds a result (full, or the partial it
          settled for); handed back at once.
        * ``"joined"``: the turn-start fetch timed out but is still running (or has since landed);
          waited for what is left of ``timeout`` counted from when that fetch STARTED, and it
          finished in that time. ``on_wait`` is called once, just before blocking on a fetch that
          is still running, so the caller can say so.
        * ``"pending"``: that fetch is STILL running when that time is up; ``(None, "pending")``.
          The caller goes on without it rather than start a second identical assembly that would
          only compete with the first for the same store. The person has already waited the whole
          budget for the turn-start collect, so this does not wait a second budget on top of it:
          a store too big to assemble in one budget used to cost two (64 s before the worker
          started instead of 33 s) for a result that was dropped anyway.
        * ``""``: there is nothing to reuse (no assembler, no turn-start fetch this turn, or it
          failed); ``(None, "")``, and the caller assembles for itself."""
        try:
            with self.lock:
                if self.turn_start_result is not None:
                    return self.turn_start_result, "reused"
                query = self.turn_start_query
                future = self.futures.get(query) if query else None
                began = self.turn_start_began
            if future is None:
                return None, ""
            left = timeout if began is None else max(0.0, timeout - (time.monotonic() - began))
            if not future.done() and left > 0 and on_wait is not None:
                try:
                    on_wait()
                except Exception:  # noqa: BLE001  a status callback must never break the wait
                    pass
            try:
                assembled = future.result(timeout=left)
            except FuturesTimeoutError:
                return None, "pending"
            except Exception:  # noqa: BLE001  the fetch itself failed; the caller tries its own
                return None, ""
            with self.lock:
                if not bool(getattr(assembled, "partial", False)):
                    self.results[query] = assembled
                self.futures.pop(query, None)
                self.turn_start_result = assembled
            return assembled, "joined"
        except Exception:  # noqa: BLE001
            return None, ""

    def register_result(self, query: str, assembled: Any) -> None:
        """Record a completed AssembledContext so a same-query read is a pure cache hit. Never raises.

        Only a FULL result belongs here: a PARTIAL one (``assembled.partial``) would displace the
        fresh, deadline-free assemble a later mid-loop read could run to recover the full fuse --
        the caller uses ``discard_prefetch`` for that case instead of registering."""
        if not query or assembled is None:
            return
        try:
            with self.lock:
                self.results[query] = assembled
                self.futures.pop(query, None)
        except Exception:  # noqa: BLE001
            pass

    def discard_prefetch(self, query: str) -> None:
        """Drop a registered pre-fetch future without caching anything. Never raises.

        Used when the turn-start prefetch resolved to a PARTIAL result: that future is already
        done holding the partial, so leaving it registered would hand the same partial to every
        mid-loop read. Discarding it makes the next same-query read fall through to the fresh
        assemble path, which runs with the deadline-free ``self.meta`` and recovers the FULL
        result."""
        if not query:
            return
        try:
            with self.lock:
                self.futures.pop(query, None)
        except Exception:  # noqa: BLE001
            pass

    def assemble_for_query(self, query: str, timeout: float):
        """Assembled context for ``query`` plus a one-word ORIGIN ("cache" | "prefetch" | "fresh").

        Serves a completed result, else waits on a registered pre-fetch future (kept referenced even
        after a turn-start timeout), else runs a fresh bounded assemble. Raises ``TimeoutError`` when
        the wait exceeds ``timeout`` (the caller turns that into a NAMED timeout observation, never
        empty); the still-running future stays referenced so a later read can reuse it.

        A PARTIAL result (``assembled.partial``, e.g. a deadline-bounded turn-start prefetch that
        landed late) is served to THIS read -- better than nothing -- but never cached as the
        query's completed result: its future is dropped instead, so the NEXT same-query read falls
        through to a fresh assemble with the deadline-free ``self.meta`` and recovers the full fuse.
        """
        if self.assembler is None:
            return None, "none"
        with self.lock:
            if query in self.results:
                return self.results[query], "cache"
            future = self.futures.get(query)
            origin = "prefetch" if future is not None else "fresh"
            if future is None:
                if self.executor is None:
                    self.executor = ThreadPoolExecutor(max_workers=1)
                assembler = self.assembler
                meta = self.meta
                future = self.executor.submit(lambda: assembler.assemble(query, meta=meta))
                self.futures[query] = future
        assembled = future.result(timeout=timeout)  # may raise TimeoutError -> named error obs
        with self.lock:
            if not bool(getattr(assembled, "partial", False)):
                self.results[query] = assembled
            self.futures.pop(query, None)
        return assembled, origin

    def render_card(self, card_id: str, timeout: float):
        """One card's rendered content plus an ORIGIN ("card" | "unsupported" | "none"). Never the
        loop's job to know the store type: dispatched via getattr, so an assembler without the
        optional ``render_card`` returns ("unsupported"). Raises ``TimeoutError`` on a slow store."""
        if self.assembler is None:
            return None, "none"
        fn = getattr(self.assembler, "render_card", None)
        if not callable(fn):
            return None, "unsupported"
        meta = self.meta

        def call_render() -> Optional[str]:
            try:
                return fn(card_id, meta=meta)
            except TypeError:
                # An assembler whose render_card does not accept meta (older/stub): call positionally.
                return fn(card_id)

        with self.lock:
            if self.executor is None:
                self.executor = ThreadPoolExecutor(max_workers=1)
            future = self.executor.submit(call_render)
        return future.result(timeout=timeout), "card"

    def close(self) -> None:
        """Shut the fresh-assemble executor down non-blocking (a still-running late fetch finishes on
        its own; Python threads cannot be force-killed). Never raises."""
        try:
            if self.executor is not None:
                self.executor.shutdown(wait=False)
        except Exception:  # noqa: BLE001
            pass


class Emitter:
    """Per-run event router. The loop calls ``emit(...)`` / ``status(...)``; this forwards a ProgressEvent to the run's
    ProgressSink (chosen by Mode) and to the status callback. It also exposes ``maybe_detach()`` so a LIVE run can drop to
    the background sink mid-flight (the live to background handoff). The loop NEVER decides
    what surfaces: it only emits; the sink decides.
    """

    def __init__(self, sink: Optional[ProgressSink], mode: Mode,
                 status_cb: Callable[[str], None],
                 detach_check: Optional[Callable[[], bool]] = None,
                 on_detach: Optional[Callable[[], None]] = None):
        self._sink = sink
        self.mode = mode
        self._status_cb = status_cb
        self._detach_check = detach_check
        self._on_detach = on_detach
        self._detached = False

    def emit(self, event: ProgressEvent) -> None:
        self.maybe_detach()
        if self._sink is not None:
            try:
                self._sink.update(event, self.mode)
            except Exception:  # noqa: BLE001  a sink must never break the run
                pass

    def status(self, text: str) -> None:
        # The status callback plus a STATUS progress event.
        try:
            self._status_cb(text)
        except Exception:  # noqa: BLE001
            pass
        self.emit(ProgressEvent(type=EVENT_STATUS, text=text))

    def maybe_detach(self) -> None:
        """If a detach was requested (consumer disconnected), switch to the background sink
        for the rest of the run, ONCE."""
        if self._detached or self._detach_check is None:
            return
        try:
            if self._detach_check():
                self._detached = True
                if self._on_detach is not None:
                    self._on_detach()
                self.mode = Mode.BACKGROUND
        except Exception:  # noqa: BLE001
            pass
