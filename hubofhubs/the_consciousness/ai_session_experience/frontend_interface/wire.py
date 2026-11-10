"""Frontend Interface arm ``json_wire``: the session's event and control contract as plain data a separate frontend can render.

An event or control crosses the wire as the dict ``to_dict`` writes (tuples as lists), and ``snapshot`` folds the events and the controls the person sent
into one picture of the run: status, goal, what the work serves, the latest of each step, the helpers with their parent and solution, cost, files changed,
the messages sent and whether the harness took each up, the open question, and how it ended. Everything is a string, number, boolean, list or dict, so
``json.dumps`` takes it as it is, and nothing in it is specific to a terminal (no escape codes, key hints or fixed widths). An event of a type this
version does not know is kept apart under ``unknown_events`` and never stops the picture. Built from the contract's own ``to_dict``, ``event_from_dict``
and ``control_from_dict``; standard library plus the hub."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Control, Finished, Review, RunStarted, SessionEvent, Step, Steer, Usage, Waiting, control_from_dict, event_from_dict)


def event_of(item: Any) -> Optional[SessionEvent]:
    """An event from an object or its dict form; ``None`` for a type nobody knows."""
    if isinstance(item, SessionEvent):
        return item
    try:
        return event_from_dict(item)
    except (ValueError, TypeError, AttributeError):
        return None


def control_of(item: Any) -> Optional[Control]:
    if isinstance(item, Control):
        return item
    try:
        return control_from_dict(item)
    except (ValueError, TypeError, AttributeError):
        return None


def changed_files(steps: Mapping[str, Step], final: Optional[Finished]) -> List[str]:
    """The files changed: every edit step that did not fail, then the ones the run reported at its end, each once."""
    names: Dict[str, None] = {}
    for step in steps.values():
        if step.kind == "edit" and step.state != "failed" and step.label:
            names.setdefault(step.label)
    for name in (final.changed if final else ()):
        names.setdefault(name)
    return list(names)


def snapshot_of(events: Sequence[Any], controls: Sequence[Any] = (), structure: Any = None) -> Dict[str, Any]:
    """The picture of the run after ``events`` and ``controls``. ``structure`` is the result of Structure In View, carried along when given."""
    facts: Dict[str, Any] = {"status": "idle", "goal": "", "harness": "", "session_id": "", "serves": {"solution": "", "milestone": "", "frame": "", "metric": "",
                                                                                                          "metric_before": None, "metric_after": None}}
    steps: Dict[str, Step] = {}
    helpers: Dict[str, Dict[str, Any]] = {}
    messages: List[Dict[str, Any]] = []
    cost: Dict[str, Any] = {"usd": None, "tokens": None, "calls": None, "cache_read_tokens": None, "cache_write_tokens": None}
    asking: Optional[Waiting] = None
    final: Optional[Finished] = None
    reviews: List[str] = []
    unknown: List[Any] = []
    for control in (c for c in map(control_of, controls or ()) if isinstance(c, Steer)):
        messages.append({"message_id": control.message_id, "text": control.text, "agent_id": control.agent_id, "taken_up": False})
    for raw in events or ():
        event = event_of(raw)
        if event is None:
            unknown.append(raw if isinstance(raw, Mapping) else str(raw))
            continue
        if isinstance(event, RunStarted):
            facts["goal"], facts["harness"] = event.goal or facts["goal"], event.harness or facts["harness"]
            facts["session_id"] = event.session_id or facts["session_id"]
            serves = facts["serves"]
            for name in ("solution", "milestone", "frame", "metric"):
                serves[name] = getattr(event, name) or serves[name]
            serves["metric_before"] = event.metric_before if event.metric_before is not None else serves["metric_before"]
            facts["status"], final, asking = "running", None, None
        elif isinstance(event, Step):
            if event.kind == "message-received":
                for message in messages:
                    if not message["taken_up"] and (message["message_id"] == event.step_id or message["text"] == event.label or event.step_id == ""):
                        message["taken_up"] = True
                        break
            old = steps.get(event.step_id)
            if old is not None and not event.label:
                event = Step(at=event.at, agent_id=old.agent_id, step_id=event.step_id, kind=old.kind, label=old.label, state=event.state, detail=event.detail)
            steps[event.step_id or f"step-{len(steps)}"] = event
            if facts["status"] == "waiting":
                facts["status"], asking = "running", None
        elif isinstance(event, AgentStarted):
            helpers[event.agent_id] = {"agent_id": event.agent_id, "parent_id": event.parent_id, "task": event.task, "solution": event.solution,
                                       "state": "running", "calls": 0}
        elif isinstance(event, AgentEnded):
            helper = helpers.setdefault(event.agent_id, {"agent_id": event.agent_id, "parent_id": "main", "task": event.agent_id, "solution": "", "calls": 0})
            helper["state"], helper["calls"] = event.state, event.calls or helper["calls"]
        elif isinstance(event, Waiting):
            asking, facts["status"] = event, "waiting"
        elif isinstance(event, Usage):
            for name, value in (("usd", event.cost_usd), ("tokens", event.tokens), ("calls", event.calls), ("cache_read_tokens", event.cache_read_tokens),
                                ("cache_write_tokens", event.cache_write_tokens)):
                cost[name] = value if value is not None else cost[name]
        elif isinstance(event, Review):
            reviews.append(event.text or "done")
        elif isinstance(event, Finished):
            final, asking = event, None
            facts["status"] = "stopped" if event.outcome == "stopped" else "finished"
            facts["session_id"] = event.session_id or facts["session_id"]
            cost["usd"] = event.cost_usd if event.cost_usd is not None else cost["usd"]
            cost["tokens"] = event.tokens if event.tokens is not None else cost["tokens"]
            facts["serves"]["metric_after"] = event.metric_after
    blocked = [f"{s.label}: {s.detail or 'blocked'}" for s in steps.values() if s.state == "blocked"]
    for line in (final.blocked if final else ()):
        if line not in blocked:
            blocked.append(line)
    out: Dict[str, Any] = dict(facts)
    out.update({"steps": [s.to_dict() for s in steps.values()], "helpers": list(helpers.values()), "cost": cost, "changed": changed_files(steps, final),
                "messages": messages, "reviews": reviews,
                "pending_input": ({"ask_id": asking.ask_id, "question": asking.question, "risky": asking.risky, "preview": asking.preview,
                                   "options": list(asking.options)} if asking is not None else None),
                "outcome": final.outcome if final else "", "report": final.report if final else "", "error": final.error if final else "",
                "blocked": blocked, "unseen": list(final.unseen) if final else [], "structure": structure, "unknown_events": unknown})
    return out


@implementation("frontend-interface", "json_wire")
class JsonWire:
    """The contract's own dict forms, folded into one JSON-ready picture of the session."""
    REQUIRES = ()

    def snapshot(self, events: Sequence[Any], controls: Sequence[Any] = (), structure: Any = None) -> Mapping[str, Any]:
        return snapshot_of(events, controls, structure)

    def encode_event(self, event: Any) -> Mapping[str, Any]:
        return event_of(event).to_dict() if event_of(event) is not None else {}

    def decode_event(self, data: Mapping[str, Any]) -> SessionEvent:
        return event_from_dict(data)

    def encode_control(self, control: Any) -> Mapping[str, Any]:
        found = control_of(control)
        return found.to_dict() if found is not None else {}

    def decode_control(self, data: Mapping[str, Any]) -> Control:
        return control_from_dict(data)
