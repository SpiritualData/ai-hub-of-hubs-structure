"""The whole hub's answer: ``hubofhubs.run("hub-of-hubs", "what is the latest Rust release?")`` returns a ``Result``.

``Result`` is what the composition arm of ``assemble-the-whole`` returns: the answer, the sources and remembered cards behind it
(``items``), the work trace, the arms that ran and the events in order, so a script, a terminal and a recorded replay all read the
same value. ``needs`` lists what a setup still lacks for any id of the hub, the same lines ``run`` raises as ``Pending``. Keywords
of ``run`` override only what differs: ``arms``, ``options``, ``provided``, ``lock``, ``environ`` (which defaults to the process
environment, read once in ``hubofhubs.resolution.process_environment``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from esoi import entry as esoi_entry

from .ports.deep import ProgressEvent
from .ports.trace import progress_event, project
from .resolution import HUB, process_environment


@dataclass(frozen=True)
class Result:
    """What a run produced. ``events`` are the events of the run in order, so a recorded run can be replayed."""
    input: str
    seat: str
    answer: str = ""
    items: Tuple[Dict[str, Any], ...] = ()     # sources, papers or cards found: title, url or id, snippet
    trace: Tuple[Dict[str, Any], ...] = ()     # the work trace events, as the reader's screen may see them
    arms: Mapping[str, str] = field(default_factory=dict)   # seat -> arm used
    tokens: Optional[Mapping[str, int]] = None  # model tokens in and out, when the arm counts them
    seconds: float = 0.0
    note: str = ""                              # what the critic found wrong with the answer, empty when it held
    events: Tuple[ProgressEvent, ...] = ()

    def __str__(self) -> str:
        return self.answer

    def to_dict(self) -> Dict[str, Any]:
        return {"input": self.input, "seat": self.seat, "answer": self.answer, "items": list(self.items), "trace": list(self.trace),
                "arms": dict(self.arms), "tokens": dict(self.tokens) if self.tokens else None, "seconds": round(self.seconds, 3), "note": self.note,
                "events": [e.to_dict() for e in self.events]}


def needs(target: str = "hub-of-hubs", *, arms: Optional[Mapping[str, str]] = None, options: Optional[Mapping[str, Any]] = None,
          provided: Optional[Mapping[str, Any]] = None, environ: Optional[Mapping[str, str]] = None, lock: Any = None) -> Tuple[str, ...]:
    """What your setup still needs for the solution or intent ``target``: one line per missing key, install or choice, naming what
    to set. An empty tuple means ``run(target, ...)`` can start."""
    env, sid, chosen = esoi_entry.prepare(HUB, target, process_environment() if environ is None else environ, arms)
    try:
        esoi_entry.build_handle(HUB, sid, env, chosen, options, provided, lock)
    except esoi_entry.Pending as pending:
        return tuple(pending.lines)
    return ()


def event(kind: str, text: str = "", **data: Any) -> ProgressEvent:
    return ProgressEvent(type=kind, text=text, data=data)


def trace_event(trace_id: str, solution: str, kind: str, label_key: str, state: str, **fields: Any) -> ProgressEvent:
    raw = {"step_id": solution, "solution_id": solution, "kind": kind, "label_key": label_key, "state": state, **fields}
    return progress_event(project(raw, trace_id=trace_id))


def hit_items(hits: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for hit in hits:
        row = hit if isinstance(hit, Mapping) else vars(hit)
        out.append({k: row[k] for k in ("title", "url", "doi", "snippet", "date", "source", "passage_kind") if row.get(k)})
    return out
