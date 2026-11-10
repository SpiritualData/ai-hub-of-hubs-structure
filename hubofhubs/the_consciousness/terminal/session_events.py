"""The contract between a harness (whatever does the deep work) and a surface (a terminal, a chat page, a task modal): typed events going out
of the run, typed controls going in. Nothing here knows a harness, a screen or a consumer, and every value is plain data, so a web surface can
carry the same shapes as JSON (``to_dict`` and ``from_dict``).

Events (a harness emits, a surface draws): ``RunStarted``, ``Step`` (read, edit, run, check, tool, delegate, note, or ``message-received`` when
the harness took up a message the person sent), ``AgentStarted`` and ``AgentEnded`` (a helper, with its parent), ``Review``, ``Waiting`` (the run
cannot go on without the person), ``Usage`` (cost, tokens and calls so far) and ``Finished`` (how it ended, what changed, the session to resume).

Controls (a surface sends, a harness takes): ``Stop``, ``Resume``, ``Steer``, ``Approve`` and ``Refuse``, each able to name one agent. A harness
declares in ``Capabilities`` which controls it can honour, and a surface shows the others as not available instead of pretending.

The latest ``Step`` with a ``step_id`` replaces earlier ones, so a surface that is replayed or reconnects draws the same screen.
"""
from __future__ import annotations

import typing
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

MAIN = "main"

STEP_KINDS = ("read", "edit", "run", "check", "tool", "delegate", "note", "message-received")
STEP_STATES = ("running", "done", "failed", "blocked")
OUTCOMES = ("met", "unmet", "stopped", "failed")
AGENT_STATES = ("running", "met", "unmet", "stopped", "failed", "not_started")


@dataclass(frozen=True)
class SessionEvent:
    """What every event carries: its ``type``, the seconds since the run began (``at``, 0 when the harness cannot tell) and the agent it is about."""
    type: str = ""
    at: float = 0.0
    agent_id: str = MAIN

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for item in fields(self):
            value = getattr(self, item.name)
            out[item.name] = list(value) if isinstance(value, tuple) else value
        return out


@dataclass(frozen=True)
class RunStarted(SessionEvent):
    type: str = "run-started"
    goal: str = ""
    harness: str = ""
    session_id: str = ""
    resumed: bool = False
    solution: str = ""            # the solution and milestone the work serves, the frame it was given, and the metric before it began
    milestone: str = ""
    frame: str = ""
    metric: str = ""
    metric_before: Optional[float] = None


@dataclass(frozen=True)
class Step(SessionEvent):
    type: str = "step"
    step_id: str = ""
    kind: str = "note"
    label: str = ""
    state: str = "done"
    detail: str = ""


@dataclass(frozen=True)
class AgentStarted(SessionEvent):
    type: str = "agent-started"
    parent_id: str = MAIN
    task: str = ""
    solution: str = ""            # the solution this helper serves, when the work follows a solution hierarchy


@dataclass(frozen=True)
class AgentEnded(SessionEvent):
    type: str = "agent-ended"
    state: str = "met"
    calls: int = 0
    summary: str = ""


@dataclass(frozen=True)
class Review(SessionEvent):
    type: str = "review"
    text: str = ""
    corrections: int = 0


@dataclass(frozen=True)
class Waiting(SessionEvent):
    type: str = "waiting"
    ask_id: str = ""
    question: str = ""
    risky: str = ""
    preview: str = ""             # what will change if the person approves
    options: Tuple[str, ...] = ("approve", "refuse")


@dataclass(frozen=True)
class Usage(SessionEvent):
    type: str = "usage"
    cost_usd: Optional[float] = None
    tokens: Optional[int] = None
    calls: Optional[int] = None


@dataclass(frozen=True)
class Finished(SessionEvent):
    type: str = "finished"
    outcome: str = "unmet"
    report: str = ""
    changed: Tuple[str, ...] = ()
    session_id: str = ""
    error: str = ""
    cost_usd: Optional[float] = None
    tokens: Optional[int] = None
    unseen: Tuple[str, ...] = ()
    metric_after: Optional[float] = None
    blocked: Tuple[str, ...] = ()     # what was refused or blocked, each with its reason


EVENTS: Dict[str, type] = {cls.__dataclass_fields__["type"].default: cls
                           for cls in (RunStarted, Step, AgentStarted, AgentEnded, Review, Waiting, Usage, Finished)}


def event_from_dict(data: Mapping[str, Any]) -> SessionEvent:
    """The event ``to_dict`` wrote. Raises ``ValueError`` for a type nobody knows (a surface shows an unknown event as one generic row)."""
    cls = EVENTS.get(str(data.get("type")))
    if cls is None:
        raise ValueError(f"unknown session event type {data.get('type')!r}")
    hints = typing.get_type_hints(cls)
    values: Dict[str, Any] = {}
    for item in fields(cls):
        if item.name in data:
            value = data[item.name]
            values[item.name] = tuple(value) if "Tuple" in str(hints.get(item.name)) and isinstance(value, (list, tuple)) else value
    return cls(**values)


# --- controls -----------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Control:
    """What a surface sends. ``agent_id`` empty means the whole run."""
    type: str = ""
    agent_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {item.name: getattr(self, item.name) for item in fields(self)}


@dataclass(frozen=True)
class Stop(Control):
    type: str = "stop"


@dataclass(frozen=True)
class Resume(Control):
    type: str = "resume"


@dataclass(frozen=True)
class Steer(Control):
    type: str = "steer"
    text: str = ""
    message_id: str = ""


@dataclass(frozen=True)
class Approve(Control):
    type: str = "approve"
    ask_id: str = ""


@dataclass(frozen=True)
class Refuse(Control):
    type: str = "refuse"
    ask_id: str = ""
    reason: str = ""


CONTROLS: Dict[str, type] = {cls.__dataclass_fields__["type"].default: cls for cls in (Stop, Resume, Steer, Approve, Refuse)}


def control_from_dict(data: Mapping[str, Any]) -> Control:
    cls = CONTROLS.get(str(data.get("type")))
    if cls is None:
        raise ValueError(f"unknown control type {data.get('type')!r}")
    return cls(**{item.name: data[item.name] for item in fields(cls) if item.name in data})


@dataclass(frozen=True)
class Capabilities:
    """The controls a harness honours and the events it can give. ``steer_ack`` is True when the harness reports ``message-received`` itself;
    ``live_usage`` when it reports cost while it works; ``live_agents`` when helpers are announced as they start (not only when they end)."""
    stop: bool = True
    resume: bool = True
    steer: bool = False
    approve: bool = False
    target_agents: bool = False
    live_usage: bool = False
    live_agents: bool = False
    steer_ack: bool = True


@typing.runtime_checkable
class Harness(typing.Protocol):
    """What a surface drives: the hub's own loop, a Claude Code stream session, an ACP agent, anything that can say these two things.

    ``start`` runs the goal to its end, calling ``sink`` with each event from the run's thread, and returns the ``Finished`` it also sent. With
    ``resume_session_id`` it continues what an earlier ``Finished`` named. ``control`` takes a control from any thread and says whether the
    harness accepted it now (False: not supported, or not ready; the surface keeps a steer and tries again)."""
    name: str
    capabilities: Capabilities

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished: ...

    def control(self, control: Control) -> bool: ...


def short(text: Any, chars: int = 100) -> str:
    one = " ".join(str(text or "").split())
    return one if len(one) <= chars else one[:max(chars - 3, 0)] + "..."


__all__ = ["AGENT_STATES", "AgentEnded", "AgentStarted", "Approve", "Capabilities", "Control", "Finished", "Harness", "MAIN", "OUTCOMES", "Refuse",
           "Resume", "Review", "RunStarted", "STEP_KINDS", "STEP_STATES", "SessionEvent", "Step", "Steer", "Stop", "Usage", "Waiting",
           "control_from_dict", "event_from_dict", "short"]
