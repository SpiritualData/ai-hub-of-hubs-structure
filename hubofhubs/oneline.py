"""The one-line way in: ``hubofhubs.run("what is the latest Rust release?")``.

One core, ``stream``, is a generator of the hub's typed ``ProgressEvent`` values (status, work trace, tokens, result, decision,
done). ``run`` drains it, hands each event to an optional ``on_event`` callback as it happens and returns a ``Result`` built from
those same events, so a script, a terminal and a recorded replay all use the one call. The generator is the core because the work
runs inline: an event is yielded the moment it exists, a terminal can draw it live, and a caller can stop early.

The selected arm of every seat comes from the records (the metric), so nothing is wired by the caller. Keywords override only what
differs: ``arms``, ``options``, ``provided``, ``lock``, ``environ``. ``environ`` defaults to the process environment
(``hubofhubs.resolution.process_environment``, the one place the hub reads it).

Seats it can answer today, by name or alias: ``model-call`` (``ask``, the default for free text), ``search-backend`` (``search``),
``know-the-world`` (``papers``) and ``card-store`` (``recall``). When the selected arm of the seat (or one it needs) lacks a key,
an install or a choice, nothing is attempted: a ``decision`` event and a ``Needs`` error say exactly what to set.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from esoi import requirements as req

from .ports.deep import ProgressEvent
from .ports.events import EVENT_DECISION, EVENT_DONE, EVENT_RESULT, EVENT_STATUS, EVENT_TOKENS, EVENT_WORK_TRACE
from .ports.trace import progress_event, project
from .resolution import assemble, process_environment

#: name or alias -> seat id
SEATS: Dict[str, str] = {
    "ask": "model-call", "answer": "model-call", "model-call": "model-call",
    "search": "search-backend", "search-backend": "search-backend",
    "papers": "know-the-world", "scholarly": "know-the-world", "know-the-world": "know-the-world",
    "recall": "card-store", "card-store": "card-store",
}
DEFAULT_SEAT = "ask"
NEEDS_DECISION = "needs-setup"


class Needs(RuntimeError):
    """The selected arm of the seat (or one it needs) cannot run until the caller sets something. ``lines`` are the exact things to
    set or install, one per seat; ``str(error)`` joins them."""

    def __init__(self, seat: str, lines: Tuple[str, ...]):
        self.seat, self.lines = seat, tuple(lines)
        super().__init__(f"{seat} cannot run yet: " + " | ".join(self.lines))


class RunFailed(RuntimeError):
    """The seat ran and reported an error (a search service refused, a lookup found nothing it could read)."""


@dataclass(frozen=True)
class Result:
    """What a run produced. ``events`` are the same events ``on_event`` received, in order, so a recorded run can be replayed."""
    input: str
    seat: str
    answer: str = ""
    items: Tuple[Dict[str, Any], ...] = ()     # sources, papers or cards found: title, url or id, snippet
    trace: Tuple[Dict[str, Any], ...] = ()     # the work trace events, as the reader's screen may see them
    arms: Mapping[str, str] = field(default_factory=dict)   # seat -> arm used
    tokens: Optional[Mapping[str, int]] = None  # model tokens in and out, when the arm counts them
    seconds: float = 0.0
    events: Tuple[ProgressEvent, ...] = ()

    def __str__(self) -> str:
        return self.answer

    def to_dict(self) -> Dict[str, Any]:
        return {"input": self.input, "seat": self.seat, "answer": self.answer, "items": list(self.items), "trace": list(self.trace),
                "arms": dict(self.arms), "tokens": dict(self.tokens) if self.tokens else None, "seconds": round(self.seconds, 3),
                "events": [e.to_dict() for e in self.events]}


def seat_of(seat: Optional[str]) -> str:
    name = SEATS.get((seat or DEFAULT_SEAT).strip().lower())
    if name is None:
        raise ValueError(f"seat {seat!r} is not one run can answer; use one of: {', '.join(sorted(SEATS))}")
    return name


def involved(system: Any, seat: str) -> List[str]:
    """The seat and every seat its built arm needs, in order."""
    found, queue = [], [seat]
    while queue:
        sid = queue.pop(0)
        if sid in found:
            continue
        found.append(sid)
        arm = system.implementations.get(sid)
        if arm is not None:
            queue.extend(system.assembler.needs_of(arm).values())
    return found


def lines_missing(system: Any, seat: str, environ: Mapping[str, str]) -> Tuple[str, ...]:
    """What the caller must still set for ``seat`` to run: the pending line of each seat it needs that is not built, then the
    unmet requirement of each built arm (a key, a library, a program). Empty when it can run."""
    out: List[str] = []
    wanted = involved(system, seat)
    for sid in list(system.pending):     # a pending seat that names another pending seat ("needs search-backend") brings its line
        if sid in wanted:
            wanted += [other for other in system.pending if other not in wanted and other in system.pending[sid]]
    for sid in wanted:
        if sid in system.pending:
            out.append(system.pending[sid])
        elif sid in system.implementations:
            line = req.remedy_line(req.blocking(req.check(req.declared(system.implementations[sid]), environ)))
            if line:
                out.append(f"{sid} ({system.choices[sid].name}): {line}")
    return tuple(out)


def needs(seat: Optional[str] = None, *, arms=None, options=None, provided=None, environ=None, lock=None) -> Tuple[str, ...]:
    """What your setup still needs for ``seat`` (default: the seat ``run`` answers free text with): one line per missing key,
    install or choice, naming what to set. An empty tuple means ``run`` can start."""
    env = process_environment() if environ is None else environ
    sid = seat_of(seat)
    system = assemble(arms=arms, options=options, provided=provided, environ=env, lock=lock)
    return lines_missing(system, sid, env)


def event(kind: str, text: str = "", **data: Any) -> ProgressEvent:
    return ProgressEvent(type=kind, text=text, data=data)


def trace_event(trace_id: str, solution: str, kind: str, label_key: str, state: str, **fields: Any) -> ProgressEvent:
    raw = {"step_id": solution, "solution_id": solution, "kind": kind, "label_key": label_key, "state": state, **fields}
    return progress_event(project(raw, trace_id=trace_id))


def hit_items(hits: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for hit in hits:
        row = hit if isinstance(hit, Mapping) else vars(hit)
        out.append({k: row[k] for k in ("title", "url", "doi", "snippet", "date", "source") if row.get(k)})
    return out


def stream(input: str, seat: Optional[str] = None, *, arms: Optional[Mapping[str, str]] = None, options: Optional[Mapping[str, Any]] = None,
           provided: Optional[Mapping[str, Any]] = None, environ: Optional[Mapping[str, str]] = None, lock: Any = None,
           model: Optional[str] = None, limit: int = 5) -> Iterator[ProgressEvent]:
    """The core: run ``input`` through ``seat`` and yield the events as they happen. The last event is always ``done``. A seat that
    cannot run yet yields one ``decision`` event (``decision_id`` ``needs-setup``, ``data["lines"]`` what to set) and then ``done``
    with ``result_kind`` ``needs``; nothing else is attempted. ``model`` names the model for ``ask`` (the arm's own default when
    omitted); ``limit`` is how many hits to keep."""
    began = time.monotonic()
    sid = seat_of(seat)
    env = process_environment() if environ is None else environ
    trace_id = f"run-{int(began * 1000) % 10**9}"
    yield event(EVENT_STATUS, f"{sid}: starting")
    system = assemble(arms=arms, options=options, provided=provided, environ=env, lock=lock)
    missing = lines_missing(system, sid, env)
    used = {s: system.choices[s].name for s in involved(system, sid) if s in system.choices}
    if missing:
        yield ProgressEvent(type=EVENT_DECISION, text="; ".join(missing), decision_id=NEEDS_DECISION,
                            data={"question": f"{sid} needs setup before it can run", "done": "the lines below are set", "lines": list(missing), "seat": sid})
        yield ProgressEvent(type=EVENT_DONE, result_kind="needs", data={"seat": sid, "lines": list(missing)})
        return
    items: List[Dict[str, Any]] = []
    tokens: Optional[Dict[str, int]] = None
    answer = ""
    if sid == "model-call":
        yield event(EVENT_STATUS, "asking the model")
        if "model-call" in (provided or {}):
            answer = system["model-call"].complete(input, model or "")
        else:
            provider = system["call-a-model"]
            before = (getattr(provider, "tokens_in", 0) or 0, getattr(provider, "tokens_out", 0) or 0)
            answer = provider.answer([{"role": "user", "content": input}], model=model)
            after = (getattr(provider, "tokens_in", 0) or 0, getattr(provider, "tokens_out", 0) or 0)
            if after != before:
                tokens = {"in": after[0] - before[0], "out": after[1] - before[1]}
                yield event(EVENT_TOKENS, f"{tokens['in']} in, {tokens['out']} out", **tokens)
    elif sid == "search-backend":
        yield trace_event(trace_id, sid, "sources", "workTrace.search", "running")
        response = system[sid].search(input, max_results=limit)
        items = hit_items(response.hits)
        answer = response.answer
        yield trace_event(trace_id, sid, "sources", "workTrace.search", "done", counts={"found": len(items)},
                          items=[{"url": i.get("url"), "label": i.get("title"), "kind": "found"} for i in items])
    elif sid == "know-the-world":
        yield trace_event(trace_id, sid, "papers", "workTrace.papers", "running")
        obs = system[sid].search(input, max_results=limit)
        if obs.kind == "error":
            yield trace_event(trace_id, sid, "papers", "workTrace.papers", "failed")
            raise RunFailed(obs.error or "the lookup returned an error")
        items = hit_items(obs.hits)
        answer = obs.text or ""
        yield trace_event(trace_id, sid, "papers", "workTrace.papers", "done", counts={"found": len(items)},
                          items=[{"ref": i.get("doi") or i.get("url") or i.get("title"), "label": i.get("title")} for i in items if i.get("title")])
    else:
        yield event(EVENT_STATUS, "searching the cards")
        cards = system[sid].search(input, limit=limit)
        items = [{"id": c.id, "text": c.text, **({"source": c.source} if c.source else {}), **({"tags": list(c.tags)} if c.tags else {})} for c in cards]
        answer = "\n".join(c["text"] for c in items)
    yield ProgressEvent(type=EVENT_RESULT, text=answer, result_kind="answer",
                        data={"answer": answer, "items": items, "arms": used, "seat": sid, "tokens": tokens, "seconds": time.monotonic() - began})
    yield ProgressEvent(type=EVENT_DONE, result_kind="answer", data={"seat": sid})


def run(input: str, seat: Optional[str] = None, *, on_event: Optional[Callable[[ProgressEvent], None]] = None, **overrides: Any) -> Result:
    """Answer ``input`` with the best-measured arm of ``seat`` (default ``ask``) and return a ``Result``.

    ``on_event`` receives every event as it happens (the same ones ``Result.events`` keeps). Keywords are those of ``stream``:
    ``arms={seat: arm}``, ``options``, ``provided={seat: object}``, ``lock``, ``environ``, ``model``, ``limit``. Raises ``Needs`` when
    the seat cannot run until something is set (its ``lines`` say exactly what), ``RunFailed`` when the seat reports an error.
    There is no resume argument: a blocked run is run again once the lines are set."""
    seen: List[ProgressEvent] = []
    for one in stream(input, seat, **overrides):
        seen.append(one)
        if on_event is not None:
            on_event(one)
    sid = seat_of(seat)
    ask = next((e for e in seen if e.type == EVENT_DECISION and e.decision_id == NEEDS_DECISION), None)
    if ask is not None:
        raise Needs(sid, tuple(ask.data["lines"]))
    done = next(e for e in seen if e.type == EVENT_RESULT).data
    return Result(input=input, seat=sid, answer=done["answer"], items=tuple(done["items"]),
                  trace=tuple(e.data for e in seen if e.type == EVENT_WORK_TRACE), arms=done["arms"], tokens=done["tokens"],
                  seconds=done["seconds"], events=tuple(seen))
