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
import json
import os
import re
from dataclasses import replace
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_adapters import LoopLines, StreamJson, loop_log_events, progress_events
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, Approve, Capabilities, Control, Finished, Notice, Refuse, RunStarted, SessionEvent, Step, Steer, Stop, Usage, Waiting, short)
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
        structured = bool(getattr(runner, "emits_session", False))
        self.capabilities = Capabilities(stop=True, resume=True, steer=True, approve=gate is not None, target_agents=False, live_usage=structured,
                                         live_agents=structured, steer_ack=structured)
        self.stopped = threading.Event()
        self.run_id = ""
        self.pending: List[Tuple[str, str]] = []
        self.sink: Callable[[SessionEvent], None] = lambda event: None
        self.lock = threading.Lock()

    def inbox_empty(self) -> bool:
        queue_ = self.runner.running.get(self.run_id)
        return queue_ is None or queue_.empty()

    def take_up(self, label: str) -> None:
        """The loop reported a message taken up: it is no longer waiting."""
        with self.lock:
            for index, (_id, text) in enumerate(self.pending):
                if short(text) == label:
                    del self.pending[index]
                    break

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
        structured = bool(getattr(self.runner, "emits_session", False))      # the runner reports the contract's own events: nothing is guessed
        lines = LoopLines()
        if self.gate is not None:
            self.gate.bind(sink, self.stopped.is_set)
        if not structured:
            sink(RunStarted(goal=goal, harness=self.name, session_id=session_id, resumed=bool(resume_session_id)))

        def emit(event: Any) -> None:
            for item in progress_events(event, loop=None if structured else lines):
                if structured and isinstance(item, Step) and item.kind == "message-received":
                    self.take_up(item.label)
                sink(item)
            if not structured:
                self.poll()
        result, usage, why = self.runner.work(goal, working_dir=self.working_dir, max_calls=self.max_calls, emit=emit, cancel_check=self.stopped.is_set,
                                              run_id=self.run_id, session_id=session_id, resume_session_id=resume_session_id or None)
        if not structured:
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
    """A runner with the Claude Code stream contract as a ``Harness``. Optional runner methods: ``approve(ask_id, allowed, reason)``, and for one helper
    ``stop_agent(task_id)``, ``steer_agent(task_id, text, message_id)`` and ``delivered_messages()`` (``[(task id, message id)]`` the helper has read since the last call); a helper is
    named to the runner by the id the CLI gave its task, which the stream's task lines tell (``StreamJson.task_ids``). A message to a helper is shown as taken up (a ``message-received``
    step with the helper's id) only when the runner says the helper read it; a helper the stream has not announced yet cannot be reached, so the control is not accepted and the surface tries again."""
    name = "stream"

    def __init__(self, runner: Any, root: str = ""):
        self.runner, self.root = runner, root
        self.capabilities = Capabilities(stop=True, resume=True, steer=True, approve=hasattr(runner, "approve"), target_agents=hasattr(runner, "stop_agent"),
                                         live_usage=True, live_agents=True, steer_ack=True)
        self.stopped = threading.Event()
        self.inbox: List[ControlMessage] = []
        self.texts: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.sink: Callable[[SessionEvent], None] = lambda event: None
        self.stream: Optional[StreamJson] = None
        self.stopping: Dict[str, None] = {}          # helpers the person stopped: their end is reported as stopped
        self.quiet: Dict[str, None] = {}             # ids of notes the hub wrote to the main session itself
        self.aimed: Dict[str, str] = {}              # message id -> the helper it was sent to

    def below(self, agent_id: str) -> List[str]:
        """``agent_id`` and every helper under it, from the stream's tree."""
        found, parents = [agent_id], dict(self.stream.agents) if self.stream else {}
        for _ in range(len(parents)):
            more = [child for child, parent in parents.items() if parent in found and child not in found]
            if not more:
                break
            found.extend(more)
        return found

    def poll_delivered(self) -> None:
        """Tell the surface which messages to helpers were read."""
        if not hasattr(self.runner, "delivered_messages") or self.stream is None:
            return
        by_task = {task: ident for ident, task in self.stream.task_ids.items()}
        for task, message_id in self.runner.delivered_messages():
            agent = by_task.get(task) or self.aimed.get(message_id, MAIN)
            self.sink(Step(agent_id=agent, step_id=message_id, kind="message-received", label=short(self.texts.get(message_id, ""))))

    def claim(self) -> List[ControlMessage]:
        with self.lock:
            got, self.inbox = self.inbox, []
        return got

    def task_of(self, agent_id: str) -> Optional[str]:
        """The id the runner knows a helper by: the CLI's task id when the runner says it names helpers that way (``by_task_id``), else the id the stream gave."""
        if not getattr(self.runner, "by_task_id", False):
            return agent_id
        return self.stream.task_ids.get(agent_id) if self.stream else None

    def stop_helper(self, agent_id: str) -> bool:
        """Stop one helper and the helpers under it; False when the runner cannot or the stream has not told the CLI's id of one of them yet."""
        if not hasattr(self.runner, "stop_agent") or self.stream is None:
            return False
        ids = self.below(agent_id)
        tasks = [self.task_of(ident) for ident in ids]
        if not tasks[0]:
            return False
        done = [bool(self.runner.stop_agent(task)) for task in tasks if task]
        if all(done):
            for ident in ids:
                self.stopping[ident] = None
        return bool(done) and all(done)

    def steer_helper(self, agent_id: str, text: str, message_id: str) -> bool:
        """Send a message to one running helper; it is taken up when the helper reads it at its next tool call."""
        if not hasattr(self.runner, "steer_agent") or self.stream is None:
            return False
        task = self.task_of(agent_id)
        if not task or agent_id in self.stream.ended:
            return False
        with self.lock:
            self.texts[message_id], self.aimed[message_id] = text, agent_id
        sent = bool(self.runner.steer_agent(task, text, message_id))
        if sent:       # the main session is told, as the person's own words, what was said to the helper (a helper's report of it reads like data to the main session; this does not)
            name = self.stream.labels.get(agent_id, "a helper")
            fyi = f"For your information, I sent this message directly to the helper \"{name}\" while it worked: {text}"
            note_id = message_id + "-fyi"
            with self.lock:
                self.quiet[note_id] = None
                self.inbox.append(ControlMessage(id=note_id, text=fyi))
        return sent

    def seen(self, ids: List[str], where: str) -> None:
        for message_id in ids:
            if message_id in self.quiet:       # the note that tells the main session about a message to a helper is not a note of the person's to show
                continue
            self.sink(Step(step_id=message_id, kind="message-received", label=short(self.texts.get(message_id, ""))))

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        self.stopped.clear()
        self.sink = sink
        stream = self.stream = StreamJson(self.root)
        self.stopping.clear()
        run_id = short_id()
        sink(RunStarted(goal=goal, harness=self.name, session_id=resume_session_id, resumed=bool(resume_session_id)))
        sink(Step(step_id="starting", kind="note", label="starting the session", state="running"))     # the first seconds show that the run began

        def emit(event: Any) -> None:
            for item in progress_events(event, stream=stream):
                if isinstance(item, AgentEnded) and item.agent_id in self.stopping and item.state == "met":
                    item = replace(item, state="stopped")        # the person stopped it: it reported what it had and ended
                if isinstance(item, AgentEnded) and item.cost_usd is None and hasattr(self.runner, "agent_cost") and stream.task_ids.get(item.agent_id):
                    item = replace(item, cost_usd=self.runner.agent_cost(stream.task_ids[item.agent_id]))       # a helper's own cost, priced from its own record
                sink(item)
            self.poll_delivered()
        quit_ = threading.Event()

        def tick() -> None:
            while not quit_.wait(0.25):
                self.poll_delivered()
        if hasattr(self.runner, "delivered_messages"):
            threading.Thread(target=tick, daemon=True).start()
        control = RunControl(claim_inputs=self.claim, mark_seen=self.seen, cancel_requested=self.stopped.is_set, poll_seconds=0.02)
        wanted = inspect.signature(self.runner.run_goal).parameters
        extra: Dict[str, Any] = {"control": control} if "control" in wanted else {}
        try:
            result = self.runner.run_goal(goal=goal, brief="", emit=emit, run_id=run_id, resume_session_id=resume_session_id or None,
                                          cancel_check=self.stopped.is_set, **extra)
        finally:
            quit_.set()
        changed = list(stream.changed)
        for note in getattr(result, "observations", None) or []:
            name = str(note).replace("changed ", "", 1)
            if name not in changed:
                changed.append(name)
        outcome = ("stopped" if result.cancelled or result.paused else "met" if result.met else "failed" if result.launch_failed else "unmet")
        still = list(stream.open_agents)
        if outcome == "met" and still:      # a run is not met while a helper it started is still working
            outcome = "unmet"
            result.error = result.error or f"{len(still)} helper{'' if len(still) == 1 else 's'} still running when the main session ended"
        why = str(getattr(result, "end_reason", "") or "")
        if why.startswith("resume_stopped:"):          # the hub's own iteration was put to the stop decision and refused: one line with its reason
            sink(Notice(kind="decision", decision="stop", reason=why.split(":", 1)[1]))
        elif why.startswith("stopped_at_hard_limit"):
            sink(Notice(kind="hard-limit", reason=why.split(":", 1)[-1]))
        spend, seconds = getattr(result, "spend_usd", None), getattr(result, "elapsed_seconds", None)
        done = Finished(outcome=outcome, report=result.output or "", changed=tuple(changed), session_id=result.session_id or stream.session_id,
                        error=result.error or "", cost_usd=result.cost_usd or None, tokens=result.tokens or None, unseen=tuple(result.unseen_inputs or ()),
                        end_reason=why, outside=tuple(str(item) for item in getattr(result, "outside_folder", None) or ()),
                        spend_usd=float(spend) if spend else None, elapsed_seconds=float(seconds) if seconds else None)
        sink(done)
        return done

    def control(self, control: Control) -> bool:
        if isinstance(control, Stop):
            if control.agent_id:
                return self.stop_helper(control.agent_id)
            self.stopped.set()
            return True
        if isinstance(control, Steer):
            if control.agent_id:
                return self.steer_helper(control.agent_id, control.text, control.message_id or short_id())
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


class Limited:
    """Tells a surface the ceilings a run was given (``Usage`` with ``ceiling_usd`` and ``ceiling_seconds``, once at each start) so it can show spend and time
    against them. With ``spend_now`` (a function of the monotonic time the run began, giving the estimated spend so far, or None) the spend is also reported every ``every`` seconds while the run works,
    since a session's own cost arrives only when it ends."""

    def __init__(self, harness: Any, *, ceiling_usd: Optional[float] = None, ceiling_seconds: Optional[float] = None,
                 spend_now: Optional[Callable[[float], Optional[float]]] = None, every: float = 2.0):
        self.harness, self.ceiling_usd, self.ceiling_seconds, self.spend_now, self.every = harness, ceiling_usd, ceiling_seconds, spend_now, every
        self.name, self.capabilities = harness.name, harness.capabilities

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        sink(Usage(ceiling_usd=self.ceiling_usd, ceiling_seconds=self.ceiling_seconds))
        quit_ = threading.Event()
        began = time.monotonic()

        def tick() -> None:
            last = None
            while not quit_.wait(self.every):
                try:
                    spent = self.spend_now(began) if self.spend_now else None
                except Exception:  # noqa: BLE001 -- an estimate that fails is no estimate
                    spent = None
                if spent and spent != last:
                    last = spent
                    sink(Usage(cost_usd=spent, ceiling_usd=self.ceiling_usd, ceiling_seconds=self.ceiling_seconds))
        ticker = threading.Thread(target=tick, daemon=True)
        if self.spend_now:
            ticker.start()
        try:
            return self.harness.start(goal, sink, resume_session_id)
        finally:
            quit_.set()

    def control(self, control: Control) -> bool:
        return self.harness.control(control)


class Tailed:
    """Gives a runner that does not forward its stream lines the steps of its work anyway, by reading the session's own record while the run goes: each new line of it
    (the same assistant and user lines, with tool calls and results, that a stream session prints) goes through ``StreamJson``. ``locate(resume_session_id, began)`` returns the
    record's path (or None while there is none); lines already in a resumed session's record are left alone. A harness that forwards its own lines is unharmed: a step with the
    same id replaces itself. ``root`` is the run's folder, whose prefix is left off the paths shown."""

    def __init__(self, harness: Any, locate: Callable[[str, float], Optional[str]], every: float = 0.3, root: str = ""):
        self.harness, self.locate, self.every, self.root = harness, locate, every, root.rstrip("/") + "/" if root else ""
        self.name, self.capabilities = harness.name, harness.capabilities

    def local(self, line: bytes) -> bytes:
        """``line`` with the run's folder left off the paths inside it (only where a name follows, so a sentence that ends with the folder keeps it)."""
        return re.sub(re.escape(self.root.encode()) + rb"(?=[A-Za-z0-9_.-])", b"", line) if self.root else line

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        began = time.monotonic()
        stream = StreamJson()
        quit_ = threading.Event()
        state: Dict[str, Any] = {"path": None, "offset": 0, "tail": b""}
        if resume_session_id:
            try:
                found = self.locate(resume_session_id, began)
                if found:
                    state["path"], state["offset"] = found, os.path.getsize(found)
            except Exception:  # noqa: BLE001 -- no record is no steps, never a failure
                pass

        def read() -> None:
            try:
                if state["path"] is None:
                    state["path"] = self.locate("", began)
                if state["path"] is None:
                    return
                with open(state["path"], "rb") as handle:
                    handle.seek(state["offset"])
                    data = state["tail"] + handle.read()
                    state["offset"] += len(data) - len(state["tail"])
            except Exception:  # noqa: BLE001
                return
            *whole, state["tail"] = data.split(b"\n")
            for line in whole:
                try:
                    raw = json.loads(self.local(line))      # a path inside the run's folder is shown relative to it
                except ValueError:
                    continue
                if isinstance(raw, dict) and raw.get("type") in ("assistant", "user") and not raw.get("isSidechain"):
                    for item in stream.events(raw):
                        sink(item)

        def tick() -> None:
            while not quit_.wait(self.every):
                read()
        thread = threading.Thread(target=tick, daemon=True)
        thread.start()
        try:
            return self.harness.start(goal, sink, resume_session_id)
        finally:
            quit_.set()
            thread.join(timeout=2)
            read()

    def control(self, control: Control) -> bool:
        return self.harness.control(control)


class Briefed:
    """Adds standing text after the goal that the harness is given but the person's screen is not (``note``, set or changed between runs): the recap of an earlier run
    when the person switched harness, or the instruction to start a helper's description with the solution it serves. The run still shows the goal as typed."""

    def __init__(self, harness: Any, note: str = ""):
        self.harness, self.note = harness, note
        self.name, self.capabilities = harness.name, harness.capabilities

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = "") -> Finished:
        if not self.note:
            return self.harness.start(goal, sink, resume_session_id)

        def shown(event: SessionEvent) -> None:
            sink(replace(event, goal=goal) if isinstance(event, RunStarted) else event)
        return self.harness.start(goal + "\n\n" + self.note, shown, resume_session_id)

    def control(self, control: Control) -> bool:
        return self.harness.control(control)


__all__ = ["ApprovalGate", "Briefed", "Framed", "Limited", "LoopHarness", "Refused", "StreamHarness", "Tailed"]
