"""Scripted harnesses, so a session can be watched, tested and scored with no model: the same script of turns runs on the hub's own loop (a scripted
completion behind ``SolutionLoopRunner``) and on a fake that keeps the stream runner's contract (``run_goal(..., control=RunControl)``, raw stream-json lines,
``approve``, ``stop_agent``). A script is a list of turns; a turn is a list of beats (read, edit, run, delegate, use, report) and an optional ``hook`` that
runs while the turn is being worked, which is where a test presses a key. Standard library and the hub only."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.terminal.session_harnesses import ApprovalGate, Framed, LoopHarness, StreamHarness
from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent

SEARCH, DIVIDER, REPLACE = "<" * 7 + " SEARCH", "=" * 7, ">" * 7 + " REPLACE"
RISKY = ("deploy",)
COST_PER_TURN = 0.0042


@dataclass
class Beat:
    kind: str
    label: str = ""
    text: str = ""
    turns: Tuple["Turn", ...] = ()


@dataclass
class Turn:
    beats: List[Beat] = field(default_factory=list)
    hook: Optional[Callable[[], None]] = None
    fired: bool = False


def read(path: str) -> Beat:
    return Beat("read", path)


def edit(path: str, text: str = "done\n") -> Beat:
    return Beat("edit", path, text)


def run(command: str) -> Beat:
    return Beat("run", command)


def use(name: str, given: str = "") -> Beat:
    return Beat("use", name, given)


def report(text: str) -> Beat:
    return Beat("report", text=text)


def delegate(task: str, *turns: "Turn") -> Beat:
    return Beat("delegate", task, turns=tuple(turns))


def turn(*beats: Beat, hook: Optional[Callable[[], None]] = None) -> Turn:
    return Turn(list(beats), hook)


@dataclass
class Trace:
    """What the scripted model was given, per turn, and what ran."""
    prompts: List[str] = field(default_factory=list)
    deployed_when_asked: Optional[bool] = None
    refused: bool = False
    calls: int = 0

    def heard(self, index: int, text: str) -> bool:
        return 0 <= index < len(self.prompts) and text in self.prompts[index]


@dataclass
class Kit:
    harness: Any
    trace: Trace
    folder: str
    runner: Any


def seed(folder: str) -> None:
    for name, text in (("README.md", "A small project.\n"), ("CHANGELOG.md", "# Changes\n")):
        path = Path(folder) / name
        if not path.exists():
            path.write_text(text)


def deploy(folder: str, given: str) -> str:
    Path(folder, "deployed.txt").write_text(given or "deployed\n")
    return "deployed"


# --- the hub's own loop, behind a scripted completion ----------------------------------------------------------------------------------

def compile_reply(turn_: Turn) -> str:
    lines: List[str] = []
    for beat in turn_.beats:
        if beat.kind == "read":
            lines.append(f"READ: {beat.label}")
        elif beat.kind == "edit":
            lines.append(f"{beat.label}\n{SEARCH}\n{DIVIDER}\n{beat.text}{REPLACE}")
        elif beat.kind == "run":
            lines.append(f"RUN: {beat.label}")
        elif beat.kind == "use":
            lines.append(f"USE: {beat.label} {beat.text}".rstrip())
        elif beat.kind == "delegate":
            lines.append(f"DELEGATE: {beat.label}")
        elif beat.kind == "report":
            lines.append(f"REPORT: {beat.text}")
    return "\n".join(lines) + "\n"


def once(item: Turn) -> Optional[Callable[[], None]]:
    """The turn's hook, which fires the first time only (a resumed run does not press the same key again)."""
    if item.hook is None:
        return None

    def fire() -> None:
        if not item.fired:
            item.fired = True
            item.hook()
    return fire


def flatten(turns: Sequence[Turn]) -> List[Tuple[str, Optional[Callable[[], None]]]]:
    out: List[Tuple[str, Optional[Callable[[], None]]]] = []
    for item in turns:
        out.append((compile_reply(item), once(item)))
        for beat in item.beats:
            if beat.kind == "delegate":
                out.extend(flatten(beat.turns))
    return out


def loop_kit(folder: str, turns: Sequence[Turn], pause: float = 0.0, max_calls: int = 20, frame: Optional[Dict[str, Any]] = None) -> Kit:
    from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import Tool
    from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner
    seed(folder)
    replies = flatten(turns)
    trace = Trace()

    def complete(system: str, prompt: str) -> str:
        index = trace.calls
        trace.calls += 1
        trace.prompts.append(prompt)
        reply, hook = replies[index] if index < len(replies) else ("BLOCKED: the script ended\n", None)
        if hook is not None:
            hook()
        if pause:
            time.sleep(pause)
        return reply

    def ask_preview(name: str, given: str) -> str:
        return f"creates deployed.txt in the working folder ({given or 'no details'}); it cannot be undone by the run"
    gate = ApprovalGate(lambda name, given: name in RISKY, preview=ask_preview)
    tools = gate.wrap({"deploy": Tool("ship the work to the live place (cannot be undone)", lambda given: deploy(folder, given))})
    runner = SolutionLoopRunner(root=folder, complete=complete, sandbox=False, review=False, session_dir=os.path.join(folder, ".sessions"), tools=tools)
    harness: Any = LoopHarness(runner, working_dir=folder, max_calls=max_calls, gate=gate)
    if frame:
        harness = Framed(harness, **frame)
    return Kit(harness, trace, folder, runner)


# --- a fake with the stream runner's contract -------------------------------------------------------------------------------------------

class ScriptedStreamRunner:
    """Satisfies the stream runner's contract: ``run_goal`` takes ``control`` (messages claimed once and confirmed with ``mark_seen``, a cancel poll) and
    reports raw stream-json lines as ``ProgressEvent(type="stream")``. A stopped run keeps its place under a session id, and ``resume_session_id`` continues
    from that place without repeating a beat."""

    def __init__(self, folder: str, turns: Sequence[Turn], trace: Trace, pause: float = 0.0):
        self.folder, self.turns, self.trace, self.pause = folder, list(turns), trace, pause
        self.places: Dict[str, Tuple[int, int]] = {}
        self.answers: Dict[str, Tuple[threading.Event, List[Any]]] = {}
        self.stopped_agents: set = set()
        self.count = 0
        self.lock = threading.Lock()

    def approve(self, ask_id: str, allowed: bool, reason: str = "") -> bool:
        found = self.answers.get(ask_id)
        if found is None or found[0].is_set():
            return False
        found[1][:] = [allowed, reason]
        found[0].set()
        return True

    def stop_agent(self, agent_id: str) -> bool:
        self.stopped_agents.add(agent_id)
        return True

    def ident(self) -> str:
        with self.lock:
            self.count += 1
            return f"tool-{self.count}"

    def run_goal(self, *, goal: str, brief: str = "", emit: Optional[Callable[[Any], None]] = None, run_id: Optional[str] = None,
                 resume_session_id: Optional[str] = None, cancel_check: Optional[Callable[[], bool]] = None, control: Any = None, **ignored: Any) -> DeepResult:
        seed(self.folder)
        session = resume_session_id or f"sess-{run_id}"
        turn_index, beat_index = self.places.get(session, (0, 0))
        say = emit or (lambda event: None)
        stopped = control.cancel_requested if control is not None else (cancel_check or (lambda: False))
        say(ProgressEvent(type="stream", data={"type": "system", "subtype": "init", "session_id": session}))
        spent = 0.0
        output = ""
        while turn_index < len(self.turns):
            current = self.turns[turn_index]
            if beat_index == 0:
                got = control.claim_inputs() if control is not None else []
                self.trace.prompts.append("\n".join(m.text for m in got))
                if got:
                    control.mark_seen([m.id for m in got], "deep_worker")
                hook = once(current)
                if hook is not None:
                    hook()
            while beat_index < len(current.beats):
                if stopped():
                    self.places[session] = (turn_index, beat_index)
                    return DeepResult(met=False, cancelled=True, session_id=session, cost_usd=spent, error="The run was stopped on request.")
                beat = current.beats[beat_index]
                if beat.kind == "report":
                    output = beat.text
                elif not self.beat(beat, say, "", stopped):
                    self.places[session] = (turn_index, beat_index)
                    return DeepResult(met=False, cancelled=True, session_id=session, cost_usd=spent, error="The run was stopped on request.")
                beat_index += 1
                if self.pause:
                    time.sleep(self.pause)
            spent += COST_PER_TURN
            say(ProgressEvent(type="stream", data={"type": "result", "total_cost_usd": round(spent, 4), "num_turns": turn_index + 1,
                                                   "usage": {"input_tokens": 400 * (turn_index + 1), "output_tokens": 120 * (turn_index + 1)}}))
            turn_index, beat_index = turn_index + 1, 0
        self.places[session] = (turn_index, 0)
        return DeepResult(met=True, output=output, session_id=session, cost_usd=spent, tokens=520 * len(self.turns))

    def beat(self, beat: Beat, say: Callable[[Any], None], parent: str, stopped: Callable[[], bool]) -> bool:
        """Run one beat. False when the run was stopped while the beat waited."""
        ident = self.ident()

        def tool_use(name: str, given: Dict[str, Any]) -> None:
            say(ProgressEvent(type="stream", data={"type": "assistant", "parent_tool_use_id": parent or None,
                                                   "message": {"content": [{"type": "tool_use", "id": ident, "name": name, "input": given}]}}))

        def result(error: bool = False, ident_: str = "") -> None:
            say(ProgressEvent(type="stream", data={"type": "user", "parent_tool_use_id": parent or None,
                                                   "message": {"content": [{"type": "tool_result", "tool_use_id": ident_ or ident, "is_error": error}]}}))
        if beat.kind == "read":
            tool_use("Read", {"file_path": beat.label})
            result()
        elif beat.kind == "edit":
            tool_use("Edit", {"file_path": beat.label})
            Path(self.folder, beat.label).write_text(beat.text)
            result()
        elif beat.kind == "run":
            tool_use("Bash", {"command": beat.label})
            result()
        elif beat.kind == "delegate":
            tool_use("Task", {"description": beat.label})
            for child in beat.turns:
                hook = once(child)
                if hook is not None:
                    hook()
                for inner in child.beats:
                    if ident in self.stopped_agents:
                        result(True)
                        return True
                    if inner.kind == "report":
                        continue
                    if not self.beat(inner, say, ident, stopped):
                        return False
            result()
        elif beat.kind == "use":
            ask_id = f"ask-{ident}"
            answer: Tuple[threading.Event, List[Any]] = (threading.Event(), [])
            self.answers[ask_id] = answer
            self.trace.deployed_when_asked = Path(self.folder, "deployed.txt").exists()
            say(ProgressEvent(type="decision", decision_id=ask_id, text=f"Run {beat.label} {beat.text}?",
                              data={"risky": beat.label, "preview": f"creates deployed.txt in the working folder ({beat.text or 'no details'}); it cannot be undone by the run"}))
            while not answer[0].wait(0.02):
                if stopped():
                    return False
            if not answer[1][0]:
                self.trace.refused = True
                tool_use("Bash", {"command": f"{beat.label} {beat.text}"})
                say(ProgressEvent(type="stream", data={"type": "permission_denied", "tool_use_id": ident, "tool_name": "Bash", "reason": "you refused it"}))
                return True
            tool_use("Bash", {"command": f"{beat.label} {beat.text}"})
            deploy(self.folder, beat.text)
            result()
        return True


def stream_kit(folder: str, turns: Sequence[Turn], pause: float = 0.0, frame: Optional[Dict[str, Any]] = None) -> Kit:
    trace = Trace()
    runner = ScriptedStreamRunner(folder, turns, trace, pause)
    harness: Any = StreamHarness(runner)
    if frame:
        harness = Framed(harness, **frame)
    return Kit(harness, trace, folder, runner)


KITS = {"loop": loop_kit, "stream": stream_kit}


def demo_harness(kind: str, folder: str, pause: float = 0.6, keys: Any = None) -> Any:
    """The scripted demo: read, a change, a helper that writes tests, a risky deploy that waits for you, then the report. With scripted ``keys`` a message
    is sent during the first turn."""
    note = (lambda: keys.press("line", "name the file release-notes.md")) if keys is not None and hasattr(keys, "react") else None
    turns = [turn(read("README.md"), read("CHANGELOG.md"), hook=note),
             turn(edit("release-notes.md", "Release notes\n"), delegate("write the tests", turn(edit("tests.md", "Tests\n"), report("tests written")))),
             turn(run("echo checks pass"), use("deploy", "release 1.0")),
             turn(report("Wrote the release notes and the tests, ran the checks and deployed."))]
    frame = {"solution": "release-notes", "milestone": "ship the next release", "metric": "checks passing", "frame": "Notes, tests, then deploy once approved.",
             "measure": (lambda: 3.0 if Path(folder, "deployed.txt").exists() else 1.0)}
    return KITS[kind](folder, turns, pause=pause, frame=frame).harness


__all__ = ["Beat", "KITS", "Kit", "ScriptedStreamRunner", "Trace", "Turn", "delegate", "demo_harness", "edit", "loop_kit", "read", "report", "run", "stream_kit", "turn", "use"]
