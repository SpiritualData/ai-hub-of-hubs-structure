"""Capture what a terminal arm DRAWS, as a person would see it, with no model and no network.

Three ways to capture, one result (a ``Capture`` of timed screen snapshots):

* ``stream``: an arm that writes text and cursor codes to a stream (the reference terminal). The bytes it wrote are replayed through the terminal emulator ``pyte``
  (LGPL-3.0, an evaluation-only dependency: it is imported here and nowhere in the hub package) at the stated size, once per write, so the screen after every
  write is known, with the scrollback above it.
* ``textual``: an arm that is a Textual application: run with Textual's ``run_test`` at the stated size, the compositor's rows and styles read at a fixed pace.
* ``external``: a separate program (an ACP terminal client) in a pseudo-terminal, its output replayed through ``pyte`` (see ``terminal_presentation/external.py``).

Every snapshot holds ``rows`` (the visible screen), ``scroll`` (what has scrolled above or is kept in the transcript widget), ``live`` (the rows of the live region: the whole
screen for a stream arm, the rows outside the transcript for Textual) and the styled cells as ``(foreground, background, sample text)`` triples in RGB, or None where the
cell uses the terminal's own colour. The size is set for the arm through COLUMNS and LINES (as a terminal does), so an arm that asks the terminal for its size gets this one."""
from __future__ import annotations

import io
import os
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SIZES = ((80, 24), (120, 40), (56, 24))      # the narrow size was added in revision 2 (2026-11-11): the owner used the terminal at about 55 columns
ENV_LOCK = threading.Lock()
SGR_FAINT = re.compile(r"\x1b\[2m")
FAINT_RGB = "\x1b[38;2;114;114;114m"        # the default foreground (229) at half intensity over the default background (0): what a terminal draws for SGR 2
ERASE = re.compile(r"\x1b\[(\d+)A")
MOVES = re.compile(r"\x1b\[\d*[ABCDEFGHJf]|\r")
SGR_ALL = re.compile(r"\x1b\[[0-9;]*m")
ANSI_RGB = {"black": (0, 0, 0), "red": (205, 0, 0), "green": (0, 205, 0), "brown": (205, 205, 0), "blue": (0, 0, 238), "magenta": (205, 0, 205), "cyan": (0, 205, 205),
            "white": (229, 229, 229), "brightblack": (127, 127, 127), "brightred": (255, 0, 0), "brightgreen": (0, 255, 0), "brightbrown": (255, 255, 0),
            "brightblue": (92, 92, 255), "brightmagenta": (255, 0, 255), "brightcyan": (0, 255, 255), "brightwhite": (255, 255, 255)}
DARK_DEFAULT, LIGHT_DEFAULT = (0, 0, 0), (255, 255, 255)

Rgb = Tuple[int, int, int]


@dataclass
class Snapshot:
    at: float                              # seconds since the capture began (monotonic)
    rows: Tuple[str, ...]
    scroll: Tuple[str, ...] = ()
    live: Tuple[str, ...] = ()
    styled: Tuple[Tuple[Optional[Rgb], Optional[Rgb], str, bool], ...] = ()      # (fg, bg, sample text, fg_is_ansi_named)


@dataclass
class Capture:
    """One run of one scenario at one size."""
    kind: str
    width: int
    height: int
    snapshots: List[Snapshot] = field(default_factory=list)
    raw: str = ""                                          # what a stream arm wrote
    arrivals: List[Tuple[float, Any]] = field(default_factory=list)        # (seconds, event) as the harness sent them
    controls: List[Tuple[float, Any, bool]] = field(default_factory=list)  # (seconds, control, accepted) as the harness took them
    report: Any = None                                     # the arm's SessionReport
    seconds: float = 0.0
    sideways: int = 0                                      # widgets that scroll sideways (Textual)
    wide_rows: int = 0                                     # rows drawn in the live region that are wider than the terminal (stream)
    repaints: int = 0
    jumps: int = 0
    not_run: Tuple[str, ...] = ()
    note: str = ""
    begun: float = 0.0                                     # the monotonic clock when the capture began (a snapshot's ``at`` is seconds after it)
    labels: Dict[str, str] = field(default_factory=dict)       # the words and marker the arm's own screen uses (``allow``, ``refuse``, ``stop``, ``person``); empty: the hub's shared words

    @property
    def final(self) -> Snapshot:
        return self.snapshots[-1] if self.snapshots else Snapshot(0.0, ())

    def text_at(self, snapshot: Snapshot) -> str:
        return "\n".join(snapshot.scroll + snapshot.rows)

    def final_text(self) -> str:
        return self.text_at(self.final)

    def all_text(self) -> str:
        return "\n".join(self.text_at(s) for s in self.snapshots)


# --- the stand-in terminal --------------------------------------------------------------------------------------------------------

class Recorder(io.StringIO):
    """A stream that says it is a terminal and keeps each write with its time."""

    def __init__(self) -> None:
        super().__init__()
        self.chunks: List[Tuple[float, str]] = []
        self.flushes: List[int] = []
        self.begun = time.monotonic()

    def write(self, text: str) -> int:
        self.chunks.append((time.monotonic() - self.begun, text))
        return super().write(text)

    def flush(self) -> None:
        self.flushes.append(len(self.chunks))

    def isatty(self) -> bool:
        return True

    def groups(self) -> List[Tuple[float, str]]:
        """The writes grouped by flush: a person sees the screen only after the flush, never between an erase and the frame written with it. An arm that never flushes is read write by write."""
        if not self.flushes:
            return list(self.chunks)
        out, start = [], 0
        for end in sorted(set(self.flushes)) + [len(self.chunks)]:
            if end > start:
                out.append((self.chunks[end - 1][0], "".join(text for _, text in self.chunks[start:end])))
            start = max(start, end)
        return out


@contextmanager
def terminal_size(width: int, height: int):
    """COLUMNS and LINES set for the arm while it runs (a terminal's size as the standard library reads it), restored after."""
    with ENV_LOCK:
        old = {name: os.environ.get(name) for name in ("COLUMNS", "LINES")}
        os.environ["COLUMNS"], os.environ["LINES"] = str(width), str(height)
        try:
            yield
        finally:
            for name, value in old.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


class Timed:
    """A harness seen from outside: every event and every control with the time it passed, and nothing changed."""

    def __init__(self, inner: Any, capture: Capture, begun: float) -> None:
        self.inner, self.capture, self.begun = inner, capture, begun
        self.name = getattr(inner, "name", "harness")
        self.capabilities = inner.capabilities

    def start(self, goal: str, sink: Callable[[Any], None], resume_session_id: str = "") -> Any:
        def seen(event: Any) -> None:
            self.capture.arrivals.append((time.monotonic() - self.begun, event))
            sink(event)
        return self.inner.start(goal, seen, resume_session_id)

    def control(self, control: Any) -> bool:
        ok = self.inner.control(control)
        self.capture.controls.append((time.monotonic() - self.begun, control, bool(ok)))
        return ok

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


# --- pyte replay -------------------------------------------------------------------------------------------------------------------

def emulator(width: int, height: int):
    try:
        import pyte
    except ImportError as error:                      # pragma: no cover -- the message is the point
        raise RuntimeError("the presentation metric replays screens with the terminal emulator pyte (LGPL-3.0, evaluation only): pip install pyte") from error
    screen = pyte.HistoryScreen(width, height, history=20000, ratio=0.5)
    return screen, pyte.Stream(screen)


def row_text(line: Any, width: int) -> str:
    return "".join(line[x].data for x in range(width)).rstrip()


def colour(name: str, default: Optional[Rgb]) -> Tuple[Optional[Rgb], bool]:
    if name == "default":
        return default, False
    if name in ANSI_RGB:
        return ANSI_RGB[name], True
    if re.fullmatch(r"[0-9a-fA-F]{6}", name or ""):
        return (int(name[0:2], 16), int(name[2:4], 16), int(name[4:6], 16)), False
    return default, False


def styled_cells(screen: Any, width: int, height: int) -> Tuple[Tuple[Optional[Rgb], Optional[Rgb], str, bool], ...]:
    """Each distinct (foreground, background) pair of the visible text cells, with the first run of text that uses it."""
    seen: Dict[Tuple[Any, ...], str] = {}
    for y in range(height):
        row = screen.buffer[y]
        for x in range(width):
            char = row[x]
            if not char.data.strip():
                continue
            fg, named = colour(char.fg, None)
            bg, _ = colour(char.bg, None)
            if char.reverse:
                fg, bg = bg, fg
            if fg is None and bg is None:
                continue
            key = (fg, bg, named)
            seen[key] = seen.get(key, "") + char.data if len(seen.get(key, "")) < 12 else seen[key]
    return tuple((fg, bg, text, named) for (fg, bg, named), text in seen.items())


def replay_stream(chunks: Sequence[Tuple[float, str]], width: int, height: int) -> Tuple[List[Snapshot], Dict[str, int]]:
    """The snapshots after each group of writes (one flush), and the counts a flicker bound needs: repaints (writes of a block of three or more rows) and cursor jumps."""
    screen, stream = emulator(width, height)
    wide_screen, wide_stream = emulator(width * 4, height)
    snapshots: List[Snapshot] = []
    repaints = jumps = wide = 0
    for at, text in chunks:
        text = SGR_FAINT.sub(FAINT_RGB, text)
        stream.feed(text.replace("\n", "\r\n"))          # a terminal in its usual mode turns a line feed into a return and a line feed (ONLCR)
        visible = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\r", "", text)         # every control sequence, the cursor moves too, takes no room on a row
        jumps += len(MOVES.findall(text))
        if visible.count("\n") >= 3:                      # a frame: the header, the steps, the keys, the input line
            repaints += 1
            wide += sum(1 for line in visible.split("\n") if len(line.rstrip()) > width and not line.lstrip().startswith("ahohs "))       # the command that resumes stays whole and is soft-wrapped by the terminal (revision 2)
        history = tuple(row_text(line, width) for line in screen.history.top)
        rows = tuple(row_text(screen.buffer[y], width) for y in range(height))
        snapshots.append(Snapshot(at, rows, history, rows, styled_cells(screen, width, height)))
    return snapshots, {"repaints": repaints, "jumps": jumps, "wide_rows": wide}


def stream_peek(out: Any, width: int, height: int) -> Tuple[str, Tuple[str, ...]]:
    """``(text with the scrollback, visible rows)`` of the screen a stream arm has drawn so far: the writes replayed through the emulator. What a scripted person looks at to see that the screen answered."""
    screen, stream = emulator(width, height)
    for _, text in out.groups():
        stream.feed(text.replace("\n", "\r\n"))
    rows = tuple(row_text(screen.buffer[y], width) for y in range(height))
    return "\n".join(tuple(row_text(line, width) for line in screen.history.top) + rows), rows


def stream_capture(arm: Any, kit_harness: Any, keys: Any, size: Tuple[int, int], goal: str = "do the work", live: bool = True,
                   options: Optional[Dict[str, Any]] = None) -> Capture:
    """Run the arm's ``attend`` on a terminal of ``size`` and replay what it wrote."""
    width, height = size
    capture = Capture("stream", width, height)
    out = Recorder()
    begun = capture.begun = time.monotonic()
    harness = Timed(kit_harness, capture, begun)
    kit_harness.peek = lambda: stream_peek(out, width, height)      # a scripted person can look at the screen (a harness that wants to wait for it reads this)
    with terminal_size(width, height):
        capture.report = arm.attend(harness, goal, out, keys, tick=0.01, live=live, width=width, **(options or {}))
    capture.seconds = time.monotonic() - begun
    capture.raw = out.getvalue()
    if live:
        capture.snapshots, counts = replay_stream(out.groups(), width, height)
        capture.repaints, capture.jumps, capture.wide_rows = counts["repaints"], counts["jumps"], counts["wide_rows"]
    else:
        capture.snapshots = [Snapshot(capture.seconds, tuple(out.getvalue().splitlines()))]
    return capture


# --- Textual -----------------------------------------------------------------------------------------------------------------------

def textual_rows(app: Any) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...], Tuple[Tuple[Any, ...], ...], int]:
    """``(rows, scroll, live, styled, sideways)`` of the running application's screen: the compositor's strips, the transcript widgets' own lines, the rows outside them."""
    from textual.widgets import RichLog
    strips = app.screen._compositor.render_strips()
    rows = tuple(strip.text.rstrip() for strip in strips)
    regions = []
    scroll: List[str] = []
    sideways = 0
    for log in app.query(RichLog):
        scroll.extend(strip.text.rstrip() for strip in log.lines)
        regions.append(log.region)
    for widget in app.screen.walk_children():
        try:
            if widget.show_horizontal_scrollbar:        # a horizontal scrollbar is on screen: the content is wider than the widget
                sideways += 1
        except Exception:  # noqa: BLE001 -- a widget with no scroll
            continue
    inside = lambda y: any(r.y <= y < r.y + r.height for r in regions)
    live = tuple(text for y, text in enumerate(rows) if not inside(y))
    seen: Dict[Tuple[Any, ...], str] = {}
    for strip in strips:
        for segment in strip:
            style = segment.style
            if style is None or not segment.text.strip():
                continue
            fg = style.color.get_truecolor() if style.color is not None else None
            bg = style.bgcolor.get_truecolor() if style.bgcolor is not None else None
            if style.dim and fg is not None and bg is not None:
                fg = tuple(int((a + b) / 2) for a, b in zip(fg, bg))
            if fg is None and bg is None:
                continue
            key = (tuple(fg) if fg else None, tuple(bg) if bg else None, False)
            if key not in seen:
                seen[key] = segment.text.strip()[:12]
    styled = tuple((fg, bg, text, named) for (fg, bg, named), text in seen.items())
    return rows, tuple(scroll), live, styled, sideways


def textual_capture(arm: Any, kit_harness: Any, keys: Any, size: Tuple[int, int], goal: str = "do the work", options: Optional[Dict[str, Any]] = None,
                    make_app: Optional[Callable[[], Any]] = None, attach: Optional[Callable[..., Any]] = None, transcript_class: Any = None) -> Capture:
    """Run a Textual arm's session in ``run_test`` at ``size``, sampling the screen every 50 ms until the session ends. ``attach(app, harness, goal, keys)`` is the arm's way
    of drawing a run in an open application (the default is ``TextualSession.attending``)."""
    import asyncio
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import textual_session as session
    width, height = size
    capture = Capture("textual", width, height)
    begun = capture.begun = time.monotonic()
    harness = Timed(kit_harness, capture, begun)
    kit_harness.peek = lambda: ((capture.text_at(capture.snapshots[-1]), capture.snapshots[-1].rows) if capture.snapshots else ("", ()))
    held: Dict[str, Any] = {}

    async def drive() -> None:
        app = (make_app or session.make_app)()
        async with app.run_test(size=(width, height)) as pilot:
            transcript = (transcript_class or session.Transcript)(app.add_line)
            settings = dict(clock=time.monotonic, tick=0.01, live=False, width=width, records=None, commands=None, segments=(), panels=(), command="", representative=None,
                            stop_limits=None, headless=True, ansi=False)
            settings.update(options or {})

            def work() -> None:
                try:
                    held["report"] = (attach or (lambda a, h, g, k, t, s: arm.attending(a, h, g, t, k, "", s)))(app, harness, goal, keys, transcript, settings)
                except BaseException as error:  # noqa: BLE001 -- carried out
                    held["error"] = error
                finally:
                    held["done"] = True
            thread = threading.Thread(target=work, daemon=True)
            thread.start()
            limit = time.monotonic() + 30
            last_change = None
            while time.monotonic() < limit:
                await pilot.pause(0.05)
                rows, scroll, live, styled, sideways = textual_rows(app)
                capture.sideways = max(capture.sideways, sideways)
                snap = Snapshot(time.monotonic() - begun, rows, scroll, live, styled)
                if (rows, scroll) != last_change:
                    capture.snapshots.append(snap)
                    last_change = (rows, scroll)
                if held.get("done"):
                    await pilot.pause(0.1)
                    rows, scroll, live, styled, sideways = textual_rows(app)
                    capture.snapshots.append(Snapshot(time.monotonic() - begun, rows, scroll, live, styled))
                    break
            thread.join(2)
    asyncio.run(drive())
    if "error" in held:
        capture.note = f"raised {type(held['error']).__name__}: {held['error']}"
    capture.report = held.get("report")
    capture.seconds = time.monotonic() - begun
    return capture


def plain_capture(arm: Any, kit_harness: Any, keys: Any, goal: str = "do the work", options: Optional[Dict[str, Any]] = None) -> Tuple[str, Any]:
    """The text an arm writes to a stream that is not a terminal."""
    out = io.StringIO()
    with terminal_size(80, 24):
        report = arm.attend(kit_harness, goal, out, keys, tick=0.01, live=False, width=80, **(options or {}))
    return out.getvalue() or getattr(report, "text", ""), report
