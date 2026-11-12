"""The Textual arm of Terminal Experience: the same session contract, drawn as a full-screen application with the open-source Textual library (MIT).

What it adds to the standard-library arm, and what it keeps: the events, the keys and the controls are the shared driver's (``live.Attendance``: Escape stops and keeps the
session, ``resume`` continues it, a typed line steers and is shown as queued and then taken up, ``y`` and ``n`` answer a question, ``@name`` and ``/stop`` aim at one helper), so
every control stays shown as taken or not available. The screen is Textual's: a header, a scrolling transcript of the run (a mouse wheel and Page keys scroll it, nothing
is lost to a redraw), a live panel with the current steps, the helpers and the structure, an input line with history (Up and Down), slash-command completion (Tab after a
``/``) and the final answer rendered as markdown with the ``rich`` library. When the run ends, the transcript is printed to the terminal again so it stays in the scrollback.

It runs the same in a terminal and headless (no terminal: the app is hosted without a driver and the transcript is what ``out`` receives), so a scripted session is
scored on the same code a person uses. ``work`` (``ahohs work``) keeps one application open across runs: the prompt, follow-ups that continue the session and ``/harness``
are the shared ``WorkTerminal``, handed this arm's input line. The library is imported only inside the functions that need it; without it ``availability`` lets the
standard-library arm stand in. Everything a consumer adds (its commands, header segments, panels, front door) comes through the same options as for any arm.
"""
from __future__ import annotations

import queue
import shutil
import sys
import threading
import time
from dataclasses import replace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO

from esoi import implementation

from hubofhubs.the_consciousness.ai_session_experience.session_events import Harness
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import Attendance, LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport, SessionView, frame, report, report_parts
from hubofhubs.the_self.assembler import arm_needs as needs

SLASH_COMMANDS = ("/help", "/tree", "/open", "/close", "/stop", "/resume", "/who", "/quit")
STATUS_ROWS = 14


class Transcript:
    """The text stream a session writes to: each finished line goes to the screen (``show``) and into a buffer the caller's ``out`` receives at the end."""

    def __init__(self, show: Callable[[str], None]):
        self.show, self.buffer, self.partial = show, [], ""

    def write(self, text: str) -> int:
        self.partial += text
        while "\n" in self.partial:
            line, self.partial = self.partial.split("\n", 1)
            self.buffer.append(line)
            self.show(line)
        return len(text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False

    def keep(self, line: str) -> None:
        """A line for the buffer only (the screen draws it another way)."""
        self.buffer.append(line)

    def getvalue(self) -> str:
        return "\n".join(self.buffer) + ("\n" if self.buffer else "")


class AppKeys:
    """The key source of a hosted application: the app's key handlers call the ``press`` the driver attached."""
    waits_for_input = True

    def __init__(self, app: Any):
        self.app = app

    def attach(self, press: Callable[..., None]) -> None:
        self.app.press = press

    def detach(self) -> None:
        self.app.press = None


def make_app() -> Any:
    """The application class, built when it is needed (Textual is imported here and nowhere else)."""
    from rich.markdown import Markdown
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import Input, RichLog, Static

    class HubApp(App):
        CSS = """
        #head { height: 1; padding: 0 1; background: #005a9e; color: $text; }
        #log { height: 1fr; padding: 0 1; overflow-x: hidden; scrollbar-color: #5f87d7; scrollbar-background: #121212; }      /* the log wraps its rows (wrap=True), so nothing is wider than it: no horizontal scrollbar */
        #status { height: auto; max-height: 16; padding: 0 1; color: $text-muted; border-top: solid $primary; }
        #menu { height: auto; padding: 0 1; color: $accent; }
        #prompt { dock: bottom; }
        #prompt > .input--placeholder { color: #b0b0b0; }
        """
        BINDINGS = [Binding("escape", "stop", "stop", priority=True), Binding("ctrl+c", "interrupt", "stop", priority=True), Binding("ctrl+d", "eof", "leave", priority=True),
                    Binding("tab", "tab", "structure", priority=True), Binding("up", "up", "up", priority=True), Binding("down", "down", "down", priority=True),
                    Binding("right", "open", "open", priority=True), Binding("left", "close", "close", priority=True)]

        def __init__(self) -> None:
            super().__init__()
            self.press: Optional[Callable[..., None]] = None
            self.attendance: Optional[Attendance] = None
            self.start_hook: Callable[[], None] = lambda: None
            self.lines: "queue.Queue[Optional[str]]" = queue.Queue()
            self.history: List[str] = []
            self.position = 0
            self.reading = False
            self.ended = False
            self.drawing: "queue.Queue[Any]" = queue.Queue()

        def compose(self) -> ComposeResult:
            yield Static("", id="head")
            yield RichLog(id="log", wrap=True, markup=False, highlight=False, auto_scroll=True, min_width=20)       # min_width defaults to 78: a markdown answer was laid out 78 wide and cut at a narrower screen
            yield Static("", id="status")
            yield Static("", id="menu")
            yield Input(placeholder="type a goal, or / for commands", id="prompt")

        def on_mount(self) -> None:
            self.query_one("#prompt", Input).focus()
            threading.Thread(target=self.pump, daemon=True).start()
            self.start_hook()

        def on_unmount(self) -> None:
            self.ended = True
            self.drawing.put(None)
            self.lines.put(None)

        # --- thread-safe drawing, called from the driver's thread ------------------------------------------------------------------

        def post(self, function: Callable[..., None], *args: Any) -> None:
            """Hand a drawing call to the screen without making the driver wait for it: a pump thread applies them in order."""
            if not self.ended:
                self.drawing.put((function, args))

        def pump(self) -> None:
            while True:
                item = self.drawing.get()
                if item is None:
                    return
                try:
                    self.call_from_thread(item[0], *item[1])
                except Exception:  # noqa: BLE001 -- a screen that is gone is not the run's failure
                    if self.ended:
                        return

        def add_line(self, text: str) -> None:
            self.post(self.write_line, text)

        def write_line(self, text: str) -> None:
            self.query_one("#log", RichLog).write(Text(text))

        def add_markdown(self, text: str) -> None:
            self.post(lambda: self.query_one("#log", RichLog).write(Markdown(text)))

        def set_status(self, rows: List[str], head: str) -> None:
            self.post(self.draw_status, rows, head)

        def draw_status(self, rows: List[str], head: str) -> None:
            self.query_one("#head", Static).update(Text(head))
            self.query_one("#status", Static).update(Text("\n".join(rows[-STATUS_ROWS:])))

        def set_prompt(self, text: str) -> None:
            self.post(lambda: setattr(self.query_one("#prompt", Input), "placeholder", text))

        # --- reading a line at the prompt (WorkTerminal) ---------------------------------------------------------------------------

        def read(self, prompt: str) -> Optional[str]:
            self.reading = True
            self.set_prompt("type a goal and press Enter" if prompt.strip() == ">" else prompt)
            try:
                return self.lines.get()
            finally:
                self.reading = False

        # --- keys -------------------------------------------------------------------------------------------------------------------

        def send(self, token: str, text: str = "") -> None:
            if self.press is not None:
                self.press(token, text)

        def action_stop(self) -> None:
            self.send("esc")

        def action_interrupt(self) -> None:
            if self.press is not None:
                self.send("interrupt")
            else:
                self.lines.put(None)

        def action_eof(self) -> None:
            if self.press is not None:
                self.send("eof")
            self.lines.put(None)

        def action_tab(self) -> None:
            box = self.query_one("#prompt", Input)
            if box.value.startswith("/") and " " not in box.value:
                matches = [name for name in SLASH_COMMANDS + tuple("/" + name for name in self.extra_commands()) if name.startswith(box.value)]
                if matches:
                    box.value = matches[0] + " "
                    box.cursor_position = len(box.value)
                return
            self.send("tree")

        def extra_commands(self) -> Sequence[str]:
            return tuple(getattr(self.attendance, "commands_extra", {}) or ())

        def tree_open(self) -> bool:
            view = getattr(self.attendance, "view", None)
            return bool(view is not None and view.show_structure and not self.query_one("#prompt", Input).value)

        def action_up(self) -> None:
            if self.tree_open():
                self.send("up")
            else:
                self.recall(-1)

        def action_down(self) -> None:
            if self.tree_open():
                self.send("down")
            else:
                self.recall(1)

        def action_open(self) -> None:
            self.send("open")

        def action_close(self) -> None:
            self.send("close")

        def check_action(self, action: str, parameters: tuple) -> Optional[bool]:
            if action in ("open", "close"):
                return self.tree_open()       # Right and Left move the cursor in the line unless the structure tree is open
            return True

        def recall(self, step: int) -> None:
            if not self.history:
                return
            self.position = max(0, min(self.position + step, len(self.history)))
            box = self.query_one("#prompt", Input)
            box.value = self.history[self.position] if self.position < len(self.history) else ""
            box.cursor_position = len(box.value)

        def on_input_changed(self, event: Input.Changed) -> None:
            value = event.value
            menu = self.query_one("#menu", Static)
            if value.startswith("/") and " " not in value:
                names = SLASH_COMMANDS + tuple("/" + name for name in self.extra_commands())
                menu.update(Text("  ".join(name for name in names if name.startswith(value)) + "   (Tab completes)"))
            else:
                menu.update("")
            asking = bool(getattr(self.attendance, "asking", ""))
            if asking and value in ("y", "n"):       # a question is open: one key answers it
                event.input.value = ""
                self.send("line", value)
                return
            if value == "?":
                event.input.value = ""
                self.send("help")
                return
            self.send("typing", value)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            text = event.value
            event.input.value = ""
            self.query_one("#menu", Static).update("")
            if text.strip():
                self.history.append(text.strip())
            self.position = len(self.history)
            if self.press is not None:
                self.send("line", text)
            else:
                self.lines.put(text)

    return HubApp()


class TextualAttendance(Attendance):
    """The shared driver with a Textual screen: the plain event lines are the transcript, ``redraw`` fills the live panel, and the closing account renders the answer as markdown."""

    app: Any = None
    transcript: Transcript
    panel = True
    ansi: bool = False     # the kept transcript is printed to a real terminal when the application closes, so its closing report is styled (markdown rendered) there

    def handle(self, item: Any) -> None:
        """A note the person sent is a finished fact, so its one home is the transcript: it is written there once when it is sent (the panel keeps only how many notes wait until
        one is taken up, and the transcript then gets its ``taken up`` line)."""
        super().handle(item)
        if item[0] == "sent":
            seconds = int(self.view.now - self.view.started)
            self.painter.line(f"[{seconds // 60}:{seconds % 60:02d}] you: {item[1].text[:70]}")

    def redraw(self) -> None:
        super().redraw()
        rows = frame(self.view, max(self.width - 2, 40), color=False, transcript=True)[:-1]       # the status panel is padded one column each side       # the input line is the screen's own
        head = rows[0] if rows else ""
        keep = rows[1:]
        if self.app is not None:
            self.app.set_status(keep, head)

    def close_out(self) -> None:
        view, done = self.view, self.view.final
        rows_plain = report(view, color=self.live or self.ansi, width=max(self.width - 1, 40) if (self.live or self.ansi) else 0)
        if done is not None and done.report.strip() and self.app is not None:
            stub = replace(done, report="")
            view.final = stub
            body, tail = report_parts(view, color=False, width=max(self.width - 3, 30))       # the quiet detail and the closing wrap to the log's width, between their parts
            view.final = done
            self.transcript.write("\n")
            self.app.add_markdown(done.report.strip())
            for row in body + tail:
                self.app.add_line(row)
            for row in rows_plain:
                self.transcript.keep(row)
        else:
            for row in rows_plain:
                self.transcript.write(row + "\n")
        self.redraw()


@implementation("terminal-session", "textual_session")
class TextualSession:
    """A full-screen terminal built on the Textual library: scrollable transcript, live panel, input with history and command completion, markdown answers; every control of
    the shared driver (stop and keep, resume, steer shown as queued and taken up, helper targeting, questions answered by one key, follow-ups, harness switch)."""
    REQUIRES = (needs.TEXTUAL,)

    def __init__(self, app: Any = None, ansi: bool = False):
        self.app = app          # the running application when this arm is the one inside ``work``
        self.ansi = ansi        # the transcript will be printed to a terminal when the application closes

    def structure_lines(self, view: Any, width: int = 100) -> List[str]:
        return LiveSession().structure_lines(view, width)

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int:
        return LiveSession().converse(front_door, lines, out, viewer_id, prompt)

    # --- hosting -----------------------------------------------------------------------------------------------------------------

    def host(self, target: Callable[[Any], None], headless: bool) -> None:
        """Run the application in this thread and ``target(app)`` in a worker thread; the application closes when the target returns."""
        app = make_app()
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
        transcript = out if isinstance(out, Transcript) else Transcript(app.add_line)       # inside ``work`` the session's own transcript keeps every run
        width = int(options.get("width") or 0) or (shutil.get_terminal_size((100, 24)).columns if not options.get("headless") else 100)
        session = TextualAttendance(harness, goal, transcript, keys if keys is not None else AppKeys(app), options["clock"], options["tick"], bool(options.get("live")), width,
                                    records=options.get("records"), commands=options.get("commands"), segments=options.get("segments") or (), panels=options.get("panels") or (),
                                    command=options.get("command") or "", representative=options.get("representative"), stop_limits=options.get("stop_limits"))
        session.app, session.transcript, session.ansi = app, transcript, bool(options.get("ansi") or self.ansi)
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
        leaves the transcript on ``out`` when it closes."""
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
        """Run a ``WorkTerminal`` inside one application that stays open across its runs: it writes to the screen's transcript, reads its lines from the input, takes the app's keys
        and draws each run with this arm. When it ends, the transcript is printed to the terminal it began on, so the session stays in the scrollback."""
        real = terminal.out
        held: Dict[str, Any] = {}

        def inside(app: Any) -> None:
            transcript = Transcript(app.add_line)
            terminal.out, terminal.arm, terminal.reader, terminal.keys, terminal.live = transcript, TextualSession(app, ansi=True), app.read, AppKeys(app), False
            terminal.lines = None
            terminal.interactive = lambda: True
            held["transcript"] = transcript
            held["code"] = terminal.run(goal, resume)
        self.host(inside, headless=False)
        terminal.out = real
        real.write(held["transcript"].getvalue())
        real.flush()
        return int(held.get("code", 0))


__all__ = ["AppKeys", "TextualAttendance", "TextualSession", "Transcript", "make_app"]
