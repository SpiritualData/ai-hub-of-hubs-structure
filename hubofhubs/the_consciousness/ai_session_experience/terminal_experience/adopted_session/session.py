"""The adopted arm of Terminal Experience: the shared session driver (``live.Attendance``) drawn on the interface adopted from an existing open-source terminal agent.

The screen is the Textual interface of Mistral Vibe v2.26.1 (Apache-2.0), vendored beside this folder and driven by typed entries; this arm is what feeds it. ``AdoptedAttendance`` is the shared
driver (Escape or Ctrl-C stops and keeps the session, ``resume`` continues it, a typed line steers and is shown as sent then taken up, ``y`` and ``n`` answer a question, ``@name`` and
``/stop`` aim at one helper) with its events handed to ``adapter.ScreenAdapter``, whose typed entries the vendored widgets draw, and its keys taken from the application's input. It adds what the
base interface lacks: who the AI acts for in the header, the structure of the solutions the work serves one key away (Tab), and the metric before and after in the closing. The text the shared
driver writes (the plain event lines and the closing report) is kept in a transcript buffer, so a scripted session is scored on the same code a person uses and ``attend`` returns the same text as
every arm. The screen libraries are imported only inside the functions that need them; without them ``availability`` lets another arm stand in.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO

from esoi import implementation

from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, Harness, RunStarted, Stop, Waiting, short
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session import adapter as hub
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import Attendance, LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport, SessionView, event_line, report
from hubofhubs.the_self.assembler import arm_needs as needs

TITLE = ""      # the header names the product in full (``present.PRODUCT``) unless a consumer gives its own title


class Transcript:
    """The text stream a session writes to: each finished line goes into a buffer the caller's ``out`` receives at the end (the screen draws from typed entries, not from these lines)."""

    def __init__(self, show: Optional[Callable[[str], None]] = None):
        self.buffer: List[str] = []
        self.partial = ""

    def write(self, text: str) -> int:
        self.partial += text
        while "\n" in self.partial:
            line, self.partial = self.partial.split("\n", 1)
            self.buffer.append(line)
        return len(text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False

    def keep(self, line: str) -> None:
        self.buffer.append(line)

    def getvalue(self) -> str:
        return "\n".join(self.buffer) + ("\n" if self.buffer else "")


class AppKeys:
    """The key source of the hosted application: the application's key handlers call the ``press`` the driver attached."""
    waits_for_input = True

    def __init__(self, app: Any):
        self.app = app

    def attach(self, press: Callable[..., None]) -> None:
        self.app.press = press

    def detach(self) -> None:
        self.app.press = None


class AdoptedAttendance(Attendance):
    """The shared driver with its events given to the adapter and its text kept in the transcript buffer."""

    panel = True
    app: Any = None
    transcript: Any = None
    color: bool = False

    def __init__(self, *args: Any, title: str = "", color: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.title, self.color = title, color
        self.adapter = hub.ScreenAdapter(self.view)
        self.last: Any = None

    def give(self, items: Sequence[Any]) -> None:
        """Hand typed entries to the screen, to be applied in order on its own loop."""
        if items and self.app is not None:
            self.app.post(self.app.apply, list(items))

    # --- events and what the person did: to the screen, and the plain text to the buffer ---------------------------------------------------

    def show(self, event: Any) -> None:
        if isinstance(event, RunStarted) and not event.goal and self.goal:
            event = replace(event, goal=self.goal)
        self.events.append(event)
        self.view.apply(event)
        if isinstance(event, Waiting):
            self.asking = event.ask_id
        row = event_line(event, self.view, True)
        if row:
            self.painter.line(row)
        if isinstance(event, Finished) and event.outcome == "stopped":
            self.painter.line(f"stopped: finished work is kept; session {event.session_id or '(none)'} can be resumed")
        self.give(self.adapter.translate(event))
        if hasattr(self.keys, "react"):
            self.keys.react(event)

    def handle(self, item: Any) -> None:
        kind = item[0]
        if kind == "sent":
            message = item[1]
            self.view.sent(message.message_id, message.text, message.agent_id)
            seconds = int(self.view.now - self.view.started)
            self.painter.line(f"[{seconds // 60}:{seconds % 60:02d}] you: {short(message.text, 70)}")
            self.give([hub.NoteSent(message.message_id, message.text, message.agent_id)])
            return
        super().handle(item)
        if kind == "answered":
            self.give([hub.AskClosed(item[1])])
        elif kind == "control" and isinstance(item[1], Stop) and item[2] and not item[1].agent_id:
            self.give([hub.HubLine("stopping", "stopping: finished work is kept, and the session can be resumed")])
        elif kind == "notice":
            self.give([hub.HubLine("notice", item[1])])

    def key(self, token: str, text: str) -> None:
        super().key(token, text)
        if token == "who":
            self.give([hub.HubLine("who", row) for row in (self.view.authority or ["No representative is named for this run: the hub's default applies."])])

    # --- the screen's figures ------------------------------------------------------------------------------------------------------------------

    def redraw(self) -> None:
        super().redraw()
        if self.app is None:
            return
        figures = hub.figures_of(self.view, self.width, self.title, self.running, len(self.view.messages) - sum(1 for m in self.view.messages if m.taken_up))
        if figures != self.last:
            self.last = figures
            self.app.post(self.app.set_figures, figures)

    def close_out(self) -> None:
        """The closing, once, when the session ends: the plain report goes to the buffer, and the screen draws the answer, the detail, the outcome and the resume command."""
        width = max(self.width - 1, 40)
        for row in report(self.view, color=self.color, width=width if self.color else 0):
            self.out.write(row + "\n")
        closing = self.adapter.closing(max(self.width - 4, 36))
        if closing is not None:
            self.give([closing])
        self.redraw()
        if self.app is not None:
            self.app.settle()


@implementation("terminal-session", "adopted_session")
class AdoptedSession:
    """A full-screen terminal that starts from an existing open-source terminal agent's interface (the Textual screen of Mistral Vibe at v2.26.1, vendored and trimmed): streamed markdown
    and reasoning, tool-call rows, the diff renderer, approval and question screens, the sub-agent list and transcripts, the loading line and the input with history and slash completion,
    driven by the hub's session contract through an adapter, with who the AI acts for, the structure of the solutions served and the metric before and after added."""
    REQUIRES = (needs.TEXTUAL, needs.PYDANTIC)

    def __init__(self, app: Any = None, ansi: bool = False, *, title: str = TITLE, theme: str = "hub-dark", history_file: Any = None):
        self.app = app          # the running application when this arm is the one inside ``work``
        self.ansi = ansi        # the transcript will be printed to a terminal when the application closes
        self.title, self.theme, self.history_file = title, theme, history_file

    def structure_lines(self, view: Any, width: int = 100) -> List[str]:
        return LiveSession().structure_lines(view, width)

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int:
        return LiveSession().converse(front_door, lines, out, viewer_id, prompt)

    def capture_hooks(self) -> Dict[str, Any]:
        """How the presentation metric draws this arm: its own application and transcript (the default hooks draw ``textual_session``'s)."""
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.app import make_app
        return {"make_app": lambda: make_app(theme=self.theme), "transcript_class": Transcript}

    # --- hosting -------------------------------------------------------------------------------------------------------------------------------

    def host(self, target: Callable[[Any], None], headless: bool) -> None:
        """Run the application in this thread and ``target(app)`` in a worker thread; the application closes when the target returns. The input's history lives in a folder that
        goes away with the session."""
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.app import make_app
        failure: Dict[str, BaseException] = {}
        with tempfile.TemporaryDirectory(prefix="ahohs-input-") as folder:
            app = make_app(history_file=self.history_file or Path(folder) / "history.jsonl", theme=self.theme)

            def work() -> None:
                try:
                    target(app)
                except BaseException as error:  # noqa: BLE001 -- carried to the calling thread
                    failure["error"] = error
                finally:
                    time.sleep(0.05)
                    try:
                        app.call_from_thread(app.exit)
                    except Exception:  # noqa: BLE001
                        pass
            app.start_hook = lambda: threading.Thread(target=work, daemon=True).start()
            app.run(headless=headless)
        if "error" in failure:
            raise failure["error"]

    def attending(self, app: Any, harness: Harness, goal: str, out: Any, keys: Any, resume_session_id: str, options: Mapping[str, Any]) -> SessionReport:
        transcript = out if isinstance(out, Transcript) else Transcript()       # inside ``work`` the session's own transcript keeps every run
        width = int(options.get("width") or 0) or (shutil.get_terminal_size((100, 24)).columns if not options.get("headless") else 100)
        session = AdoptedAttendance(harness, goal, transcript, keys if keys is not None else AppKeys(app), options["clock"], options["tick"], False, width,
                                    records=options.get("records"), commands=options.get("commands"), segments=options.get("segments") or (), panels=options.get("panels") or (),
                                    command=options.get("command") or "", representative=options.get("representative"), stop_limits=options.get("stop_limits"),
                                    title=self.title, color=bool(options.get("live") or options.get("ansi") or self.ansi))
        session.app, session.transcript = app, transcript
        app.attendance = session
        try:
            session.attend(resume_session_id)
        finally:
            app.attendance = None
        final = session.runs[-1] if session.runs else None
        return SessionReport(final=final, runs=tuple(session.runs), events=tuple(session.events), controls=tuple(session.controls), view=session.view, text=transcript.getvalue())

    def attend(self, harness: Harness, goal: str, out: TextIO, keys: Any = None, resume_session_id: str = "", clock: Callable[[], float] = time.monotonic,
               tick: float = 0.02, live: Optional[bool] = None, width: int = 0, records: Any = None,
               commands: Optional[Mapping[str, Callable[[str], Optional[str]]]] = None, segments: Sequence[Callable[[SessionView], str]] = (),
               panels: Sequence[Callable[[SessionView], List[str]]] = (), command: str = "", representative: Optional[Mapping[str, Any]] = None,
               stop_limits: Optional[Mapping[str, Any]] = None) -> SessionReport:
        """Run ``goal`` on ``harness`` and return the report. Inside ``work`` it draws in the open application; on its own it hosts one (headless when ``out`` is not a terminal) and
        leaves the transcript on ``out`` when it closes. ``live`` styles the kept transcript with colour, as it is when it is printed to a terminal."""
        options = dict(clock=clock, tick=tick, live=live, width=width, records=records, commands=commands, segments=segments, panels=panels, command=command,
                       representative=representative, stop_limits=stop_limits)
        if self.app is not None:
            return self.attending(self.app, harness, goal, out, keys, resume_session_id, options)
        tty = bool(getattr(out, "isatty", lambda: False)()) and sys.stdin.isatty()
        options["headless"] = not tty
        options["ansi"] = tty
        held: Dict[str, SessionReport] = {}
        self.host(lambda app: held.__setitem__("report", self.attending(app, harness, goal, out, keys, resume_session_id, options)), headless=not tty)
        result = held["report"]
        out.write(result.text)
        out.flush() if hasattr(out, "flush") else None
        return replace(result, text=out.getvalue() if hasattr(out, "getvalue") else result.text)

    def work(self, build: Callable[[str], Harness], out: TextIO, goal: str = "", resume: str = "", lines: Optional[Iterable[str]] = None, **options: Any) -> Any:
        """The interactive command. On a terminal one application stays open across the runs (the prompt, follow-ups and ``/harness`` are ``WorkTerminal``'s); with scripted
        ``lines`` or no terminal each run is hosted headless and the text goes to ``out``."""
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.work import WorkTerminal
        tty = bool(getattr(out, "isatty", lambda: False)()) and sys.stdin.isatty() and lines is None and options.get("live") is not False
        if not tty:
            terminal = WorkTerminal(build, out, lines=lines, arm=self, **options)
            terminal.run(goal, resume)
            return terminal
        terminal = WorkTerminal(build, out, lines=None, arm=self, **options)
        terminal.code = self.host_terminal(terminal, goal, resume)
        return terminal

    def host_terminal(self, terminal: Any, goal: str = "", resume: str = "") -> int:
        """Run a ``WorkTerminal`` inside one application that stays open across its runs: it writes to a transcript buffer, reads its lines from the input, takes the application's keys and
        draws each run with this arm. When it ends the transcript is printed to the terminal it began on, so the session stays in the scrollback."""
        real = terminal.out
        held: Dict[str, Any] = {}

        def inside(app: Any) -> None:
            transcript = Transcript()
            terminal.out, terminal.arm, terminal.reader, terminal.keys, terminal.live = transcript, AdoptedSession(app, ansi=True, title=self.title, theme=self.theme), app.read, AppKeys(app), False
            terminal.lines = None
            terminal.interactive = lambda: True
            held["transcript"] = transcript
            held["code"] = terminal.run(goal, resume)
        self.host(inside, headless=False)
        terminal.out = real
        real.write(held["transcript"].getvalue())
        real.flush()
        return int(held.get("code", 0))


__all__ = ["AdoptedAttendance", "AdoptedSession", "AppKeys", "Transcript"]
