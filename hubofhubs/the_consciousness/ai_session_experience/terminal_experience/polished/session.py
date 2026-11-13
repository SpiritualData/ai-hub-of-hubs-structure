"""The polished arm of Terminal Experience: the shared session driver (``live.Attendance``) drawn on the polished full-screen application.

It is driven by the hub's own contract and nothing else: session events in (``SessionView`` is the state), typed controls out (``Stop``, ``Steer``, ``Approve``, ``Refuse``), the
keys of the shared key source. It brings down the settled rules of a polished screen and keeps them in the driver, where they can be tested without a terminal:

* a note typed while the AI works is the person's own line, counted while it waits, and shown as taken up when the harness reads it; several notes that no run took up combine into
  ONE next message in the order typed; a stopped run flushes them; a failed run starts no new message (the notes go back in the prompt box); a note is never sent as the answer to a
  question the person has not read (they go back in the box too);
* the transcript keeps what is finished, the work panel shows what is running now, and the closing is derived from structured fields only: the answer, the metric before and after
  once, the quiet detail, then one closing line with the outcome, the time and the cost.

Constructor options are the extension points for a consumer (they have defaults, so the registered arm needs none): ``title``, ``metric_rows`` (a function of the view returning the
metric lines that replace the single before-and-after one), ``persist`` (called with the view and the ``Finished`` at the end of each run), ``choices`` (the menu's choices after a
command), ``log_prefixes`` (the loggers whose warnings are shown folded) and ``log_path``. The other consumer options (``commands``, ``segments``, ``panels``, ``front_door``,
``represent``) come through ``WorkTerminal`` as for every arm. Textual is imported only inside the functions that need it.
"""
from __future__ import annotations

import queue
import shutil
import sys
import threading
import time
import uuid
from dataclasses import replace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO

from esoi import implementation

from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, Harness, Step, Steer, Usage, Waiting, short
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import agent_focus
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import Attendance, LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.markdown_text import markdown_lines
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import text as words_of
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import say
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport, SessionView, event_line
from hubofhubs.the_self.assembler import arm_needs as needs

MAX_TURNS = 8        # resumes and notes flushed into a next message, in one attended session
PLAIN = "\x1b"


class PolishedAttendance(Attendance):
    """The shared driver with the polished rules. ``live`` is always off here: the screen is the application, and ``color`` says whether the kept transcript is styled."""

    panel = True
    app: Any = None
    transcript: Any = None

    def __init__(self, *args: Any, title: str = "", metric_rows: Optional[Callable[[SessionView], List[str]]] = None, persist: Optional[Callable[[SessionView, Finished], None]] = None,
                 color: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.title, self.metric_rows, self.persist, self.color = title, metric_rows, persist, color
        self.held: List[str] = []            # notes typed while a harness that cannot take one runs: they wait for the next message
        self.unanswered = False              # a question was asked and not yet answered
        self.last_snapshot: Any = None
        self.quit_wanted = False

    # --- keys: a note is the person's own line, queued ------------------------------------------------------------------------------

    def press(self, token: str, text: str = "") -> None:
        if token == "eof":
            self.quit_wanted = True
        super().press(token, text)

    def line(self, text: str) -> None:
        text = text.strip()
        if words_of.is_note(text, running=self.running, stopping=self.stop_wanted, asking=bool(self.asking)):
            self.note(text)
        else:
            super().line(text)

    def note(self, text: str) -> None:
        if self.view.focus.path:       # a note typed inside a helper is a message to that helper: the shared driver routes it to that agent
            Attendance.line(self, text)
            return
        message = Steer(text=text, message_id=uuid.uuid4().hex[:8])
        if getattr(self.harness.capabilities, "steer", False):
            ok = self.send(message)
            if not ok:
                self.unsent.append(message)
        else:
            self.held.append(text)           # this harness cannot take a message while it works: it waits and goes with the next one
            ok = False
        self.inbox.put(("sent", message, ok))

    def key(self, token: str, text: str) -> None:
        """``?`` and ``/help`` list the polished screen's own keys, written once to the transcript (the base lists keys this screen does not have)."""
        if token == "help":
            for name in ("esc", "type", "answer", "panel", "structure", "copy"):
                self.painter.line("  " + say(f"polished.help.rows.{name}"))
            return
        super().key(token, text)

    def handle(self, item: Any) -> None:
        kind = item[0]
        if kind == "sent":
            message = item[1]
            self.view.sent(message.message_id, message.text, message.agent_id)
            self.painter.line("❯ " + say("polished.note.echo", text=message.text))
        elif kind == "answered":
            self.unanswered = False
            super().handle(item)
        else:
            super().handle(item)

    # --- the transcript: what finished (the panel shows what is happening now) --------------------------------------------------------

    def rows_for(self, event: Any) -> List[str]:
        if isinstance(event, Step) and event.kind == "message-received":
            return [f"{words_of.present.GLYPHS['done']} " + words_of.pickup_line(1)]
        if isinstance(event, Usage):
            return []
        row = self.guarded(lambda: event_line(event, self.view, True), event)
        return [row] if row else []

    def show(self, event: Any) -> None:
        self.events.append(event)
        self.view.apply(event)
        if isinstance(event, Waiting):
            self.asking, self.unanswered = event.ask_id, True
        for row in self.rows_for(event):
            self.painter.line(row)
        if hasattr(self.keys, "react"):
            self.keys.react(event)

    # --- the screen ---------------------------------------------------------------------------------------------------------------------

    def structure_rows(self) -> List[str]:
        view = self.view
        if view.show_structure and view.structure_panel:
            return list(view.structure_panel)
        return [view.structure_compact] if view.structure_compact else []

    def metric_block(self) -> List[str]:
        if self.metric_rows is not None:
            try:
                return [str(row) for row in self.metric_rows(self.view)]
            except Exception:  # noqa: BLE001 -- a consumer's metric lines that raise are left out, never fatal
                return []
        return []

    def snapshot(self) -> Any:
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import Snapshot
        view = self.view
        runs = words_of.runs_of(view)
        focus = view.focus
        agent_focus.prune(view, focus)
        inner = max(self.width - 4, 20)
        if focus.path:       # inside a helper: where the person is and that helper's own rows, the same at every depth
            rows = [(agent_focus.breadcrumb(view, focus, inner), "head")] + [(row, "step") for row in agent_focus.agent_lines(view, focus, inner, False)]
            line_map: Dict[int, str] = {}
        else:
            flat = ["  " + row for row in agent_focus.child_rows(view, focus, inner, False)]
            rows, line_map = words_of.dashboard(view, "", self.structure_rows() + list(view.panels) + flat, with_helpers=not flat)
        busy = self.running and view.status in ("running", "waiting", "stopping")
        return Snapshot(head=words_of.header_text(view, self.title, view.segments, max(self.width - 2, 20)), activity=words_of.activity_text(view), waited=view.elapsed() if busy else None,
                        queued=words_of.waiting_notes(view, len(self.held)), rows=rows, line_map=line_map, runs=[(r.agent_id, r.title) for r in runs],
                        histories={r.agent_id: words_of.history_lines(view, r.agent_id) for r in runs}, metrics=self.metric_block(),
                        prompt=words_of.prompt_state(view, self.running), busy=busy, asking=view.asking is not None,
                        stopped=view.status == "stopped" and not self.running, structure=bool(self.nodes or view.structure_compact), structure_open=view.show_structure,
                        agents_nav=not view.show_structure and bool(focus.path or any(a.state == "running" for a in agent_focus.children(view, agent_focus.MAIN))), inside=bool(focus.path))

    def redraw(self) -> None:
        super().redraw()         # the clock, the structure and the consumer's segments and panels (it draws nothing: ``live`` is off)
        if self.app is None:
            return
        snap = self.snapshot()
        if snap != self.last_snapshot:
            self.last_snapshot = snap
            self.app.post(self.app.apply_snapshot, snap)

    # --- runs, notes and the end of a run --------------------------------------------------------------------------------------------------

    def run(self, resume_session_id: str) -> Finished:
        self.view.started = self.view.now = self.clock()      # one clock per run: every time on the screen counts from here
        self.view.ended = None
        if self.app is not None:
            self.app.post(self.app.begin_run)
        return super().run(resume_session_id)

    def settle(self, done: Finished) -> List[str]:
        """The notes no run took up (typed while it worked, never read), once each in the order typed, and the queue emptied."""
        notes = words_of.leftover_notes([m.text for m in self.unsent], done.unseen, self.held)
        self.unsent.clear()
        self.held.clear()
        for message in self.view.messages:
            message.taken_up = True      # nothing is queued any more: they are sent as the next message, or back in the box
        return notes

    def give_back(self, notes: List[str]) -> None:
        """Notes that must not be sent on their own (the run failed, or a question was never read): back in the prompt box, after what the person typed there."""
        self.painter.line("  " + words_of.back_in_box_line(len(notes)))
        if self.app is not None:
            self.app.set_prompt_text(words_of.combine_notes(notes))

    def attend(self, resume_session_id: str) -> None:
        if self.keys is not None:
            self.keys.attach(self.press)
        try:
            turns = 0
            while True:
                done = self.run(resume_session_id)
                self.runs.append(done)
                if self.persist is not None:
                    try:
                        self.persist(self.view, done)
                    except Exception:  # noqa: BLE001 -- a consumer's save that raises never stops the session
                        pass
                self.redraw()
                notes = self.settle(done)
                if notes and (done.outcome == "failed" or self.unanswered):
                    self.give_back(notes)         # no new message after an error, and a note is not the answer to a question nobody has read
                    notes = []
                self.unanswered = False
                if turns >= MAX_TURNS or self.quit_wanted:
                    break
                if notes:
                    if not self.next_is_resume_or_none():
                        break
                    self.painter.line("  " + words_of.flush_line(len(notes)))
                    self.goal = words_of.combine_notes(notes)
                    resume_session_id = done.session_id
                elif done.outcome == "stopped":
                    if self.next_command() != "resume":
                        break
                    self.painter.line(f"resuming session {done.session_id}")
                    resume_session_id = done.session_id
                else:
                    break
                turns += 1
                self.stop_wanted = False
                self.asking = ""
                self.view.status = "running"
        finally:
            if self.keys is not None:
                self.keys.detach()
            self.close_out()

    def next_is_resume_or_none(self) -> bool:
        """False when a quit was typed meanwhile; a typed ``resume`` is taken (the notes go with it)."""
        try:
            return self.commands.get_nowait() != "quit"
        except queue.Empty:
            return True

    def close_out(self) -> None:
        """The closing, written once when the session ends: the answer (markdown on the screen), the metric before and after, the quiet detail, then the one closing line."""
        view, done = self.view, self.view.final
        width = max(self.width - 1, 40)
        above, closing = words_of.closing_rows(view, color=self.color, width=width if self.color else 0)
        if self.metric_rows is not None:
            above = self.metric_block() + [row for row in above if not words_of.plain(row).startswith("Metric ")]
        answer = done.report.strip() if done is not None else ""
        kept = (markdown_lines(answer, width if self.color else 0, self.color) if answer else []) + above + closing
        if self.app is None:
            for row in kept:
                self.out.write(row + "\n")
            return
        self.app.add_line("")
        if answer:
            self.app.add_markdown(answer)
        for row in above + closing:
            self.app.add_ansi(row)
        self.app.add_line("")
        self.transcript.keep("")
        for row in kept:
            self.transcript.keep(row)
        self.redraw()


@implementation("terminal-session", "polished_session")
class PolishedSession:
    """A full-screen terminal with the polished screen's settled rules (prompt docked at the bottom, a transcript that follows and selects, one activity row, a calm work panel and a
    run detail, queued notes, one closing line, folded warnings, a command menu, copy or stop or ask twice to quit), driven by the hub's own session contract."""
    REQUIRES = (needs.TEXTUAL,)
    agent_labels = {"enter": "right", "leave": "left", "message": "type", "stop": "esc"}          # the words its key line uses for the agent keys (the presentation metric reads these)
    agent_keys = {"enter": ("open", ""), "leave": ("close", ""), "next": ("down", ""), "stop": ("esc", "")}      # the keys a script presses to go into a helper, back, to the next helper and to stop the one in view

    def __init__(self, app: Any = None, ansi: bool = False, *, title: str = "", metric_rows: Optional[Callable[[SessionView], List[str]]] = None,
                 persist: Optional[Callable[[SessionView, Finished], None]] = None, choices: Optional[Callable[[str], Sequence[Any]]] = None,
                 log_prefixes: Sequence[str] = ("hubofhubs",), log_path: Any = None, verbosity: int = 0, environ: Optional[Mapping[str, str]] = None):
        self.app = app          # the running application when this arm is the one inside ``work``
        self.ansi = ansi        # the transcript will be printed to a terminal when the application closes
        self.title, self.metric_rows, self.persist, self.choices = title, metric_rows, persist, choices
        self.log_prefixes, self.log_path, self.verbosity = tuple(log_prefixes), log_path, verbosity
        self.env = dict(environ or {})      # the environment the entry point handed in (the screen reads TMUX, VTE_VERSION and the state folder from it, never from the process)

    def configure(self, **options: Any) -> None:
        """The command hands in what only an entry point may read: the process environment."""
        if "environ" in options:
            self.env = dict(options["environ"] or {})

    def structure_lines(self, view: Any, width: int = 100) -> List[str]:
        return LiveSession().structure_lines(view, width)

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int:
        return LiveSession().converse(front_door, lines, out, viewer_id, prompt)

    # --- hosting ---------------------------------------------------------------------------------------------------------------------

    def host(self, target: Callable[[Any], None], headless: bool, commands: Optional[Mapping[str, Callable[..., Any]]] = None, between_runs: bool = False) -> None:
        """Run the application in this thread and ``target(app)`` in a worker thread; the application closes when the target returns. ``between_runs`` adds the commands of the
        interactive prompt (``/harness``, ``/new``, ``/session``) to the menu."""
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import PolishedApp
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.menu import work_commands
        app = PolishedApp(title=self.title, commands=commands, choices=self.choices, log_prefixes=self.log_prefixes, log_path=self.log_path, verbosity=self.verbosity, environ=self.env)
        if between_runs:
            app.commands = app.commands + work_commands()
        failure: Dict[str, BaseException] = {}

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
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import AppKeys, Transcript
        transcript = out if isinstance(out, Transcript) else Transcript(app.add_line)       # inside ``work`` the session's own transcript keeps every run
        width = int(options.get("width") or 0) or (shutil.get_terminal_size((100, 24)).columns if not options.get("headless") else 100)
        session = PolishedAttendance(harness, goal, transcript, keys if keys is not None else AppKeys(app), options["clock"], options["tick"], False, width,
                                     records=options.get("records"), commands=options.get("commands"), segments=options.get("segments") or (), panels=options.get("panels") or (),
                                     command=options.get("command") or "", representative=options.get("representative"), stop_limits=options.get("stop_limits"),
                                     title=self.title, metric_rows=self.metric_rows, persist=self.persist, color=bool(options.get("live") or options.get("ansi") or self.ansi))
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
        self.host(lambda app: held.__setitem__("report", self.attending(app, harness, goal, out, keys, resume_session_id, options)), headless=not tty, commands=commands)
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
        """Run a ``WorkTerminal`` inside one application that stays open across its runs: it writes to the screen's transcript, reads its lines from the prompt, takes the app's keys and
        draws each run with this arm. When it ends the transcript is printed to the terminal it began on, so the session stays in the scrollback."""
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import AppKeys, Transcript
        real = terminal.out
        held: Dict[str, Any] = {}

        def inside(app: Any) -> None:
            transcript = Transcript(app.add_line)
            arm = PolishedSession(app, ansi=True, title=self.title, metric_rows=self.metric_rows, persist=self.persist, choices=self.choices, log_prefixes=self.log_prefixes,
                                  log_path=self.log_path, verbosity=self.verbosity, environ=self.env)
            terminal.out, terminal.arm, terminal.reader, terminal.keys, terminal.live = transcript, arm, app.read, AppKeys(app), False
            terminal.lines = None
            terminal.interactive = lambda: True
            held["transcript"] = transcript
            held["code"] = terminal.run(goal, resume)
        self.host(inside, headless=False, commands=terminal.extra, between_runs=True)
        terminal.out = real
        real.write(held["transcript"].getvalue())
        real.flush()
        return int(held.get("code", 0))


__all__ = ["PolishedAttendance", "PolishedSession"]
