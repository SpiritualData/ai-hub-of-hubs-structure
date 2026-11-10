"""The reference experience of working with the AI while it works: one driver for any ``Harness``, drawn in a terminal with the standard library only.

``LiveSession().attend(harness, goal, out, keys)`` runs the goal on the harness in its own thread and, in the calling thread, draws the events and takes
the person's keys: Escape or Ctrl-C stops the run at once and keeps the session, ``resume`` continues it, a typed line is sent as steering and shown
as sent, then as taken up, ``y`` and ``n`` answer a question, ``@name text`` steers and ``/stop name`` stops one helper. On a terminal the screen is
redrawn in place; anywhere else (a pipe, a file) it is plain appended lines with no escape codes. The harness is anything that satisfies
``session_events.Harness``; see ``session_harnesses`` for the hub loop and the stream runner.

Run it: ``python -m hubofhubs.the_consciousness.terminal.live --help``; ``--demo loop`` or ``--demo stream`` runs a scripted session with no model.
"""
from __future__ import annotations

import argparse
import queue
import shutil
import sys
import threading
import time
import uuid
from dataclasses import replace
from typing import Any, Callable, Dict, Iterable, List, Optional, TextIO, Tuple

from esoi import implementation

from hubofhubs.the_consciousness.terminal.repl import LineRepl
from hubofhubs.the_consciousness.terminal.session_events import (
    Approve, Control, Finished, Harness, Refuse, SessionEvent, Step, Steer, Stop, Waiting, short)
from hubofhubs.the_consciousness.terminal.session_view import SessionReport, SessionView, event_line, frame, report

MAX_RESUMES = 8
REDRAW_SECONDS = 0.1


class Painter:
    """Draws a block of lines and replaces it in place on a terminal; on anything else it only appends."""

    def __init__(self, out: TextIO, live: bool, width: int):
        self.out, self.live, self.width, self.height = out, live, width, 0

    def draw(self, lines: List[str]) -> None:
        if not self.live:
            return
        self.erase()
        self.out.write("\n".join(lines) + "\n")
        self.height = len(lines)
        self.out.flush()

    def erase(self) -> None:
        if self.live and self.height:
            self.out.write(f"\x1b[{self.height}A\r\x1b[J")
            self.height = 0

    def line(self, text: str) -> None:
        if text:
            self.erase()
            self.out.write(text + "\n")
            self.out.flush()


class Attendance:
    """One attended session: the events in, the keys in, the controls out."""

    def __init__(self, harness: Harness, goal: str, out: TextIO, keys: Any, clock: Callable[[], float], tick: float, live: bool, width: int):
        self.harness, self.goal, self.out, self.keys, self.clock, self.tick = harness, goal, out, keys, clock, tick
        self.live = live
        self.painter = Painter(out, live, width)
        self.width = width
        self.view = SessionView()
        self.view.started = self.view.now = clock()
        self.inbox: "queue.Queue[Tuple[Any, ...]]" = queue.Queue()
        self.commands: "queue.Queue[str]" = queue.Queue()
        self.events: List[SessionEvent] = []
        self.controls: List[Tuple[Control, bool]] = []
        self.runs: List[Finished] = []
        self.unsent: List[Steer] = []
        self.stop_wanted = False
        self.running = False
        self.asking = ""
        self.lock = threading.Lock()

    # --- keys, from any thread ----------------------------------------------------------------------------------------------------

    def send(self, control: Control) -> bool:
        ok = bool(self.harness.control(control))
        with self.lock:
            self.controls.append((control, ok))
        self.inbox.put(("control", control, ok))
        return ok

    def press(self, token: str, text: str = "") -> None:
        if token in ("esc", "interrupt"):
            if self.running:
                self.stop_wanted = True
                self.send(Stop())
            return
        if token == "typing":
            self.inbox.put(("typing", text))
            return
        if token == "eof":
            self.commands.put("quit")
            self.stop_wanted = self.running
            if self.running:
                self.harness.control(Stop())
            return
        if token == "line":
            self.line(text.strip())

    def line(self, text: str) -> None:
        if not text:
            return
        word = text.lower()
        if word in ("resume", "/resume"):
            if self.stop_wanted or not self.running:
                self.commands.put("resume")
            else:
                self.inbox.put(("notice", "Nothing is stopped. Press Escape to stop the run first."))
        elif word in ("quit", "/quit", "exit"):
            self.commands.put("quit")
            if self.running:
                self.stop_wanted = True
                self.send(Stop())
        elif self.asking and word in ("y", "yes", "approve", "n", "no", "refuse"):
            ask = self.asking
            self.asking = ""
            ok = self.send(Approve(ask_id=ask) if word in ("y", "yes", "approve") else Refuse(ask_id=ask, reason="you refused it"))
            self.inbox.put(("answered", ask, ok))
        elif word.startswith("/stop"):
            name = text[5:].strip()
            agent = self.view.find_agent(name) if name else ""
            if name and not agent:
                self.inbox.put(("notice", f"No single agent matches {name!r}."))
            elif not self.send(Stop(agent_id=agent)) and agent:
                self.inbox.put(("notice", "This harness cannot stop one agent; use Escape to stop the whole run."))
        elif self.running and not self.stop_wanted:
            target, body = "", text
            if text.startswith("@") and " " in text:
                name, body = text[1:].split(" ", 1)
                target = self.view.find_agent(name)
                if not target:
                    self.inbox.put(("notice", f"No single agent matches {name!r}."))
                    return
            message = Steer(text=body.strip(), agent_id=target, message_id=uuid.uuid4().hex[:8])
            ok = self.send(message)
            self.inbox.put(("sent", message, ok))
            if not ok:
                if getattr(self.harness.capabilities, "steer", False):
                    self.unsent.append(message)
                else:
                    self.inbox.put(("notice", "This harness cannot take a message while it works."))
        else:
            self.inbox.put(("notice", "Nothing is running. Type resume to continue a stopped run, or quit."))

    # --- the main thread ----------------------------------------------------------------------------------------------------------

    def show(self, event: SessionEvent) -> None:
        self.events.append(event)
        self.view.apply(event)
        if isinstance(event, Waiting):
            self.asking = event.ask_id
        if not self.live:
            self.painter.line(event_line(event, self.view))
            if isinstance(event, Finished) and event.outcome == "stopped":
                self.painter.line(f"stopped: finished work is kept; session {event.session_id or '(none)'} can be resumed")
        if hasattr(self.keys, "react"):
            self.keys.react(event)

    def handle(self, item: Tuple[Any, ...]) -> None:
        kind = item[0]
        if kind == "event":
            self.show(item[1])
        elif kind == "typing":
            self.view.typing = item[1]
        elif kind == "sent":
            message, ok = item[1], item[2]
            self.view.sent(message.message_id, message.text, message.agent_id)
            if not self.live:
                self.painter.line(f"[{int(self.view.now - self.view.started) // 60}:{int(self.view.now - self.view.started) % 60:02d}] you: {short(message.text, 70)} ({'sent' if ok else 'waiting to be sent'})")
        elif kind == "control":
            if isinstance(item[1], Stop) and item[2] and not item[1].agent_id:
                self.view.status = "stopping"
                if not self.live:
                    self.painter.line("stopping: finished work is kept, and the session can be resumed")
        elif kind == "answered":
            self.view.asking = None
            self.view.status = "running"
        elif kind == "notice":
            self.view.notice(item[1])
            if not self.live:
                self.painter.line(item[1])

    def retry(self) -> None:
        for message in list(self.unsent):
            if self.harness.control(message):
                self.unsent.remove(message)
                with self.lock:
                    self.controls.append((message, True))

    def redraw(self) -> None:
        self.view.now = self.clock()
        if self.live:
            self.painter.draw(frame(self.view, self.width, color=True))

    def run(self, resume_session_id: str) -> Finished:
        holder: Dict[str, Finished] = {}

        def work() -> None:
            try:
                holder["done"] = self.harness.start(self.goal, lambda event: self.inbox.put(("event", self.stamp(event))), resume_session_id)
            except Exception as error:  # noqa: BLE001 -- a harness that raises ends the run as failed
                holder["done"] = Finished(outcome="failed", error=f"{type(error).__name__}: {error}", session_id=resume_session_id)
                self.inbox.put(("event", holder["done"]))
        self.running, self.stop_wanted = True, False
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        last = 0.0
        try:
            while thread.is_alive() or not self.inbox.empty():
                try:
                    self.handle(self.inbox.get(timeout=self.tick))
                except queue.Empty:
                    pass
                self.retry()
                if self.clock() - last >= REDRAW_SECONDS:
                    self.redraw()
                    last = self.clock()
        except KeyboardInterrupt:
            self.press("interrupt")
            thread.join(timeout=30)
            while not self.inbox.empty():
                self.handle(self.inbox.get())
        thread.join()
        self.running = False
        return holder["done"]

    def stamp(self, event: SessionEvent) -> SessionEvent:
        """The event with the seconds since the run began, when the harness left them out."""
        return event if event.at else replace(event, at=max(self.clock() - self.view.started, 0.001))

    def attend(self, resume_session_id: str) -> None:
        if self.keys is not None:
            self.keys.attach(self.press)
        try:
            resumes = 0
            while True:
                done = self.run(resume_session_id)
                self.runs.append(done)
                self.redraw()
                if done.outcome != "stopped" or resumes >= MAX_RESUMES:
                    break
                command = self.next_command()
                if command != "resume":
                    break
                resumes += 1
                if not self.live:
                    self.painter.line(f"resuming session {done.session_id}")
                resume_session_id = done.session_id
                self.unsent.extend(Steer(text=text, message_id=uuid.uuid4().hex[:8]) for text in done.unseen)
                self.stop_wanted = False
                self.asking = ""
                self.view.status = "running"
        finally:
            if self.keys is not None:
                self.keys.detach()
            self.painter.erase()
            for row in report(self.view, color=self.live):
                self.out.write(row + "\n")
            self.out.flush()

    def next_command(self) -> str:
        """After a stop: a resume or quit already typed, or (on a terminal) wait for one. A script that typed none ends here."""
        try:
            return self.commands.get_nowait()
        except queue.Empty:
            pass
        if not getattr(self.keys, "waits_for_input", False):
            return "quit"
        self.view.status = "stopped"
        while True:
            self.handle_waiting()
            try:
                return self.commands.get(timeout=self.tick)
            except queue.Empty:
                continue

    def handle_waiting(self) -> None:
        while not self.inbox.empty():
            self.handle(self.inbox.get())
        self.redraw()


@implementation("terminal-session", "live_session")
class LiveSession:
    """Drives any harness: live view, Escape stops and keeps the session, resume, steering shown as taken up, sub-agent tree, approvals, closing report."""
    REQUIRES = ()     # the seats it is handed

    def converse(self, front_door: Callable[[str], Any], lines: Iterable[str], out: TextIO, viewer_id: str = "", prompt: str = "> ") -> int:
        return LineRepl().converse(front_door, lines, out, viewer_id, prompt)

    def attend(self, harness: Harness, goal: str, out: TextIO, keys: Any = None, resume_session_id: str = "", clock: Callable[[], float] = time.monotonic,
               tick: float = 0.02, live: Optional[bool] = None, width: int = 0) -> SessionReport:
        """Run ``goal`` on ``harness`` and return the report. ``live`` (redraw in place) defaults to whether ``out`` is a terminal."""
        tty = bool(getattr(out, "isatty", lambda: False)()) if live is None else live
        columns = width or (shutil.get_terminal_size((80, 24)).columns if tty else 80)
        session = Attendance(harness, goal, out, keys, clock, tick, tty, columns)
        session.attend(resume_session_id)
        final = session.runs[-1] if session.runs else None
        return SessionReport(final=final, runs=tuple(session.runs), events=tuple(session.events), controls=tuple(session.controls), view=session.view,
                             text=out.getvalue() if hasattr(out, "getvalue") else "")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hubofhubs.the_consciousness.terminal.live",
                                     description="Watch, stop, resume and steer an AI run from a terminal. Escape or Ctrl-C stops and keeps the session; type a line to steer; "
                                                 "type resume after a stop; y or n answers a question; @name text steers one helper; /stop name stops one.")
    parser.add_argument("--demo", choices=("loop", "stream"), help="run a scripted session with no model: the hub's own loop, or a fake Claude Code stream session")
    parser.add_argument("--goal", default="Add a changelog entry and ship it", help="the goal shown for the demo")
    parser.add_argument("--slow", type=float, default=0.6, help="seconds the demo pauses between steps, so it can be watched and interrupted")
    parser.add_argument("--plain", action="store_true", help="append plain lines even on a terminal")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    from hubofhubs.the_consciousness.terminal.scripted import demo_harness
    import tempfile
    from hubofhubs.the_consciousness.terminal.session_keys import ScriptedKeys, TtyKeys
    with tempfile.TemporaryDirectory() as folder:
        interactive = sys.stdin.isatty() and sys.stdout.isatty() and not args.plain
        keys: Any = TtyKeys() if interactive else ScriptedKeys().when("waiting", "line", "y")
        harness = demo_harness(args.demo, folder, pause=args.slow, keys=keys)
        session = LiveSession().attend(harness, args.goal, sys.stdout, keys, live=None if interactive else False)
    return 0 if session.final and session.final.outcome in ("met", "stopped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
