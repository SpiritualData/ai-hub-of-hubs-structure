"""Adapters that make a runner a ``Harness`` for the session surfaces, and the gate that makes a risky step wait for the person.

* ``LoopHarness(runner)``: the hub's own loop (``SolutionLoopRunner``). Stop sets the flag the loop polls between calls (the session is saved after
  every call, so the next ``start(resume_session_id=...)`` continues it); a steer goes to ``runner.steer`` and is shown as taken up when the loop
  has emptied its inbox; helpers are read from ``LoopResult.log`` when the run ends. Tools handed to the runner are gated by an ``ApprovalGate``.
* ``StreamHarness(runner)``: a runner with the Claude Code stream contract (``run_goal(..., control=RunControl)``). A steer is a ``ControlMessage``
  the runner claims and confirms with ``mark_seen``; stop is ``cancel_requested``; raw stream lines arrive as ``ProgressEvent(type="stream")``.
Any other runner joins by implementing ``Harness`` (``start`` and ``control``); the surfaces change nothing. Standard library and the hub only.
"""
from __future__ import annotations

import inspect
from dataclasses import replace
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from hubofhubs.the_consciousness.terminal.session_adapters import LoopLines, StreamJson, loop_log_events, progress_events
from hubofhubs.the_consciousness.terminal.session_events import (
    Approve, Capabilities, Control, Finished, Refuse, RunStarted, SessionEvent, Step, Steer, Stop, Usage, Waiting, short)
from hubofhubs.the_world.tools.delegated_agent_sessions.control import ControlMessage, RunControl


class Refused(Exception):
    """Raised inside a gated tool when the person refused it or stopped the run before answering; the loop shows the model a failed action."""


class ApprovalGate:
    """Wraps tools so that a risky call waits for the person. ``risky(name, input)`` says which; ``wait`` is the longest a question stays open."""

    def __init__(self, risky: Callable[[str, str], bool], wait: float = 600.0, preview: Callable[[str, str], str] = lambda name, given: ""):
        self.risky, self.wait, self.preview = risky, wait, preview
        self.sink: Callable[[SessionEvent], None] = lambda event: None
        self.stopped: Callable[[], bool] = lambda: False
        self.answers: Dict[str, Tuple[threading.Event, List[Any]]] = {}
        self.count = 0
        self.lock = threading.Lock()

    def bind(self, sink: Callable[[SessionEvent], None], stopped: Callable[[], bool]) -> None:
        self.sink, self.stopped = sink, stopped

    def wrap(self, tools: Mapping[str, Any]) -> Dict[str, Any]:
        from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import Tool
        return {name: Tool(description=tool.description, run=self.gated(name, tool.run)) for name, tool in tools.items()}

    def gated(self, name: str, run: Callable[[str], str]) -> Callable[[str], str]:
        def call(given: str) -> str:
            if not self.risky(name, given):
                return run(given)
            with self.lock:
                self.count += 1
                ask_id = f"ask-{self.count}"
                answer: Tuple[threading.Event, List[Any]] = (threading.Event(), [])
                self.answers[ask_id] = answer
            self.sink(Waiting(ask_id=ask_id, question=f"Run {name} {short(given, 60)}?", risky=name, preview=self.preview(name, given)))
            deadline = time.monotonic() + self.wait
            while not answer[0].wait(0.02):
                if self.stopped():
                    self.blocked(ask_id, name, given, "the run was stopped before you answered")
                    raise Refused("the run was stopped before the person answered")
                if time.monotonic() > deadline:
                    self.blocked(ask_id, name, given, "nobody answered in time")
                    raise Refused("nobody answered in time")
            allowed, reason = answer[1]
            if not allowed:
                self.blocked(ask_id, name, given, reason or "you refused it")
                raise Refused(reason or "the person refused")
            return run(given)
        return call

    def blocked(self, ask_id: str, name: str, given: str, why: str) -> None:
        self.sink(Step(step_id=ask_id + "-blocked", kind="tool", label=f"{name} {short(given, 50)}", state="blocked", detail=why))

    def answer(self, ask_id: str, allowed: bool, reason: str = "") -> bool:
        found = self.answers.get(ask_id)
        if found is None or found[0].is_set():
            return False
        found[1][:] = [allowed, reason]
        found[0].set()
        return True


def short_id() -> str:
    return uuid.uuid4().hex[:8]


class LoopHarness:
    """The hub's own loop as a ``Harness``."""
    name = "loop"

    def __init__(self, runner: Any, *, working_dir: Optional[str] = None, max_calls: int = 15, gate: Optional[ApprovalGate] = None):
        self.runner, self.working_dir, self.max_calls, self.gate = runner, working_dir, max_calls, gate
        self.capabilities = Capabilities(stop=True, resume=True, steer=True, approve=gate is not None, target_agents=False, live_usage=False,
                                         live_agents=False, steer_ack=False)
        self.stopped = threading.Event()
        self.run_id = ""
        self.pending: List[Tuple[str, str]] = []
        self.sink: Callable[[SessionEvent], None] = lambda event: None
        self.lock = threading.Lock()

    def inbox_empty(self) -> bool:
        queue_ = self.runner.running.get(self.run_id)
        return queue_ is None or queue_.empty()

    def poll(self) -> None:
        with self.lock:
            if self.pending and self.inbox_empty():
                taken, self.pending = self.pending, []
            else:
                return
        for message_id, text in taken:
            self.sink(Step(step_id=message_id, kind="message-received", label=short(text)))

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        self.stopped.clear()
        self.sink = sink
        self.run_id = short_id()
        session_id = resume_session_id or self.run_id
        lines = LoopLines()
        if self.gate is not None:
            self.gate.bind(sink, self.stopped.is_set)
        sink(RunStarted(goal=goal, harness=self.name, session_id=session_id, resumed=bool(resume_session_id)))

        def emit(event: Any) -> None:
            for item in progress_events(event, loop=lines):
                sink(item)
            self.poll()
        result, usage, why = self.runner.work(goal, working_dir=self.working_dir, max_calls=self.max_calls, emit=emit, cancel_check=self.stopped.is_set,
                                              run_id=self.run_id, session_id=session_id, resume_session_id=resume_session_id or None)
        for item in loop_log_events(result.log):
            sink(item)
        cost = float(usage.get("cost", 0.0)) or None
        tokens = int(usage.get("tokens", 0)) or None
        sink(Usage(cost_usd=cost, tokens=tokens, calls=result.calls))
        outcome = "stopped" if why == "cancelled" else "met" if result.met else "failed" if result.error.startswith("the model call failed") else "unmet"
        with self.lock:
            unseen = tuple(text for _id, text in self.pending)
        done = Finished(outcome=outcome, report=result.report, changed=tuple(result.changed), session_id=session_id, error=result.error if not result.met else "",
                        cost_usd=cost, tokens=tokens, unseen=unseen)
        sink(done)
        return done

    def control(self, control: Control) -> bool:
        if isinstance(control, Stop):
            if control.agent_id:
                return False
            self.stopped.set()
            return True
        if isinstance(control, Steer):
            if control.agent_id or not self.run_id:
                return False
            with self.lock:
                if not self.runner.steer(control.text, run_id=self.run_id):
                    return False
                self.pending.append((control.message_id or short_id(), control.text))
            return True
        if isinstance(control, (Approve, Refuse)) and self.gate is not None:
            return self.gate.answer(control.ask_id, isinstance(control, Approve), getattr(control, "reason", ""))
        return False


class StreamHarness:
    """A runner with the Claude Code stream contract as a ``Harness``. Optional runner methods: ``approve(ask_id, allowed, reason)``,
    ``stop_agent(agent_id)`` and ``steer_agent(agent_id, text)``."""
    name = "stream"

    def __init__(self, runner: Any):
        self.runner = runner
        self.capabilities = Capabilities(stop=True, resume=True, steer=True, approve=hasattr(runner, "approve"), target_agents=hasattr(runner, "stop_agent"),
                                         live_usage=True, live_agents=True, steer_ack=True)
        self.stopped = threading.Event()
        self.inbox: List[ControlMessage] = []
        self.texts: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.sink: Callable[[SessionEvent], None] = lambda event: None

    def claim(self) -> List[ControlMessage]:
        with self.lock:
            got, self.inbox = self.inbox, []
        return got

    def seen(self, ids: List[str], where: str) -> None:
        for message_id in ids:
            self.sink(Step(step_id=message_id, kind="message-received", label=short(self.texts.get(message_id, ""))))

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        self.stopped.clear()
        self.sink = sink
        stream = StreamJson()
        run_id = short_id()
        sink(RunStarted(goal=goal, harness=self.name, session_id=resume_session_id, resumed=bool(resume_session_id)))

        def emit(event: Any) -> None:
            for item in progress_events(event, stream=stream):
                sink(item)
        control = RunControl(claim_inputs=self.claim, mark_seen=self.seen, cancel_requested=self.stopped.is_set, poll_seconds=0.02)
        wanted = inspect.signature(self.runner.run_goal).parameters
        extra: Dict[str, Any] = {"control": control} if "control" in wanted else {}
        result = self.runner.run_goal(goal=goal, brief="", emit=emit, run_id=run_id, resume_session_id=resume_session_id or None,
                                      cancel_check=self.stopped.is_set, **extra)
        changed = list(stream.changed)
        for note in getattr(result, "observations", None) or []:
            name = str(note).replace("changed ", "", 1)
            if name not in changed:
                changed.append(name)
        outcome = ("stopped" if result.cancelled or result.paused else "met" if result.met else "failed" if result.launch_failed else "unmet")
        done = Finished(outcome=outcome, report=result.output or "", changed=tuple(changed), session_id=result.session_id or stream.session_id,
                        error=result.error or "", cost_usd=result.cost_usd or None, tokens=result.tokens or None, unseen=tuple(result.unseen_inputs or ()))
        sink(done)
        return done

    def control(self, control: Control) -> bool:
        if isinstance(control, Stop):
            if control.agent_id:
                return bool(hasattr(self.runner, "stop_agent") and self.runner.stop_agent(control.agent_id))
            self.stopped.set()
            return True
        if isinstance(control, Steer):
            if control.agent_id:
                return bool(hasattr(self.runner, "steer_agent") and self.runner.steer_agent(control.agent_id, control.text))
            message_id = control.message_id or short_id()
            with self.lock:
                self.texts[message_id] = control.text
                self.inbox.append(ControlMessage(id=message_id, text=control.text))
            return True
        if isinstance(control, (Approve, Refuse)) and hasattr(self.runner, "approve"):
            return bool(self.runner.approve(control.ask_id, isinstance(control, Approve), getattr(control, "reason", "")))
        return False


class Framed:
    """Gives any harness the frame of a milestone: the solution and milestone the work serves, the solution frame, and the metric before and after.
    ``measure()`` returns the metric now; it is called once before the run and once after."""

    def __init__(self, harness: Any, *, solution: str = "", milestone: str = "", frame: str = "", metric: str = "",
                 measure: Optional[Callable[[], Optional[float]]] = None):
        self.harness, self.solution, self.milestone, self.frame, self.metric, self.measure = harness, solution, milestone, frame, metric, measure
        self.name, self.capabilities = harness.name, harness.capabilities

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        before = self.measure() if self.measure and not resume_session_id else None
        kept = {"before": before}

        def framed(event: SessionEvent) -> None:
            if isinstance(event, RunStarted):
                event = replace(event, solution=self.solution, milestone=self.milestone, frame=self.frame, metric=self.metric, metric_before=kept["before"])
            sink(event)
        done = self.harness.start(goal, framed, resume_session_id)
        if self.measure and done.outcome != "stopped":
            done = replace(done, metric_after=self.measure())
            sink(done)
        return done

    def control(self, control: Control) -> bool:
        return self.harness.control(control)


__all__ = ["ApprovalGate", "Framed", "LoopHarness", "Refused", "StreamHarness"]
