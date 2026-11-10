"""The whole hub's answer: ``hubofhubs.run("hub-of-hubs", "what is the latest Rust version?")`` returns a ``Result``.

``Result`` is what the composition arm of ``the-assembler`` returns: the answer, the sources and remembered cards behind it
(``items``), the work trace, the arms that ran and the events in order, so a script, a terminal and a recorded replay all read the
same value. ``needs`` lists what a setup still lacks for any id of the hub, the same lines ``run`` raises as ``Pending``. Keywords
of ``run`` override only what differs: ``arms``, ``options``, ``provided``, ``lock``, ``environ`` (which defaults to the process
environment, read once in ``hubofhubs.the_self.assembler.resolution.process_environment``).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Tuple

from esoi import entry as esoi_entry
from esoi.runtime.assemble_by_name.entry import Runner

from hubofhubs.the_world.tools.deep import ProgressEvent
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.trace import progress_event, project
from hubofhubs.the_self.assembler.availability import stand_ins
from hubofhubs.the_self.assembler.resolution import HUB, process_environment


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
    note: str = ""                              # what the person should read: what the critic found wrong, or why the answer is weaker; empty when nothing needs saying
    events: Tuple[ProgressEvent, ...] = ()
    steps: Tuple[Dict[str, Any], ...] = ()      # the step of every part of a flow: done, skipped, or pending with the reason (no arm yet)
    stood_in: Tuple[Dict[str, str], ...] = ()   # detail, never shown by default: each solution whose selected arm could not run here and the arm that did the job instead
    stopped: str = ""                           # why the run ended early, when it did: "unavailable" (a needed step could not run), "budget", "authority", "cancelled"

    def __str__(self) -> str:
        return self.answer

    def to_dict(self) -> Dict[str, Any]:
        return {"input": self.input, "seat": self.seat, "answer": self.answer, "items": list(self.items), "trace": list(self.trace),
                "arms": dict(self.arms), "tokens": dict(self.tokens) if self.tokens else None, "seconds": round(self.seconds, 3), "note": self.note,
                "events": [e.to_dict() for e in self.events], "steps": list(self.steps), "stood_in": list(self.stood_in), "stopped": self.stopped}


def needs(target: str = "hub-of-hubs", *, arms: Optional[Mapping[str, str]] = None, options: Optional[Mapping[str, Any]] = None,
          provided: Optional[Mapping[str, Any]] = None, environ: Optional[Mapping[str, str]] = None, lock: Any = None) -> Tuple[str, ...]:
    """What your setup still needs for the solution or intent ``target``: one line per missing key, install or choice, naming what
    to set. An empty tuple means ``run(target, ...)`` can start."""
    env = process_environment() if environ is None else environ
    arms, _standing = stand_ins(HUB, env, arms, options, lock)
    env, sid, chosen = esoi_entry.prepare(HUB, target, env, arms)
    try:
        esoi_entry.build_handle(HUB, sid, env, chosen, options, provided, lock)
    except esoi_entry.Pending as pending:
        return tuple(pending.lines)
    return ()


class HubRunner(Runner):
    """``hubofhubs.run``: esoi's one-line runner, with the best-measured arm that can run here standing in for a selected arm that cannot
    (``hubofhubs.the_self.assembler.availability``). The stand-ins are recorded in ``Result.stood_in``, a detail, not a message. An arm the
    caller names in ``arms`` is kept; a solution no arm can serve is left to report its pending step."""

    def __call__(self, target: Any, input: Any = None, **overrides: Any) -> Any:
        env = overrides.pop("environ", None)
        env = process_environment() if env is None else env
        arms, standing = stand_ins(HUB, env, overrides.pop("arms", None), overrides.get("options"), overrides.get("lock"))
        got = super().__call__(target, input, environ=env, arms=arms, **overrides)
        return replace(got, stood_in=tuple(s.to_dict() for s in standing)) if standing and isinstance(got, Result) else got


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
