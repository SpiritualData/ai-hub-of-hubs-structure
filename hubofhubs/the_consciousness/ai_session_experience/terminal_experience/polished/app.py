"""The polished screen: a Textual application (MIT licence) laid out as a header, the transcript, the work panel, the run detail, and one docked bottom bar (activity row, command menu,
prompt, key line), so the prompt is always at the bottom whatever grows above it.

The application knows no harness. The shared driver (``session.PolishedAttendance``) works in its own thread and hands this screen plain text and one ``Snapshot`` at a time through
``post``; the screen sends the person's keys back through ``press`` (``esc``, ``line``, ``eof``, ...) exactly as the other arms' key sources do. Between runs (``ahohs work``) the same
screen stays open and ``read`` gives the prompt's next line to the caller. Imported only when the screen is built.
"""
from __future__ import annotations

import base64
import logging
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import menu as menu_module
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import text as words_of
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.notices import NoticeFolder
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.widgets import (
    CYAN, DIM, GREEN, MAGENTA, RED, YELLOW, ActivityBar, DetailPanel, KeyHints, PromptBox, TranscriptLog, WorkPanel, hanging)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import say


def load_libraries() -> None:
    """Bind the Textual and Rich names this module's classes are built on. The imports are inside a function, as the import boundary requires of every library of an extra
    (``tests/test_import_boundary.py``); this module is imported only when the screen is built (``session.py`` imports it inside a function), so nothing needs the extra before then."""
    from rich.markdown import Markdown
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.widgets import OptionList, Static
    from textual.widgets.option_list import Option
    globals().update(Markdown=Markdown, Text=Text, App=App, ComposeResult=ComposeResult, Binding=Binding, Vertical=Vertical, OptionList=OptionList, Static=Static, Option=Option)


load_libraries()

QUIT_CONFIRM_SECONDS = 3.0       # after a first Ctrl+C a second within this quits; long enough to read the line, short enough that a stray press minutes later never counts
QUIT_GRACE_SECONDS = 2.0         # how long the screen waits for a stopping run before it closes anyway

CLIPBOARD_COMMANDS = (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["wl-copy"])
MARK = ("ok", "..", "!!", "xx")


@dataclass
class Snapshot:
    """Everything the screen draws that the driver knows, as plain data (so the screen never reads the driver's state from its own thread)."""
    head: str = ""
    activity: str = ""
    waited: Optional[float] = None
    queued: int = 0
    rows: List[Tuple[str, str]] = field(default_factory=list)
    line_map: Dict[int, str] = field(default_factory=dict)
    runs: List[Tuple[str, str]] = field(default_factory=list)       # (agent id, title) of each run that can be opened
    histories: Dict[str, List[str]] = field(default_factory=dict)
    metrics: List[str] = field(default_factory=list)
    prompt: str = "ready"
    busy: bool = False
    asking: bool = False
    stopped: bool = False
    structure: bool = False
    structure_open: bool = False
    agents_nav: bool = False         # a helper is in view or one is running: the arrows walk the agents
    inside: bool = False             # a helper is in view (not the main run)


def copy_with_tool(text: str, which: Callable[[str], Any] = shutil.which, run: Optional[Callable[..., Any]] = None) -> Tuple[bool, str]:
    """Try each known clipboard program: ``(copied, why not)``. ``which`` and ``run`` can be replaced, so it is testable without a clipboard."""
    run = run or subprocess.run
    found: Optional[str] = None
    installed = False
    for command in CLIPBOARD_COMMANDS:
        if which(command[0]) is None:
            continue
        installed = True
        try:
            run(command, input=text.encode(), check=True, capture_output=True, timeout=2)
            return True, ""
        except Exception as error:  # noqa: BLE001
            found = f"{command[0]} failed: {type(error).__name__}"
    return False, found or ("no clipboard program is installed (install wl-clipboard or xclip)" if not installed else "the clipboard program failed")


def style_line(text: str) -> Text:
    """A transcript line as the screen draws it: a finished step coloured by how it ended, a question in the question colour, a warning in the warning colour, a note of the person's own in bold cyan."""
    body = text.split("] ", 1)[1] if text.startswith("[") and "] " in text else text
    style = ""
    if body.startswith(("✓ ", "ok ")):
        style = GREEN
    elif body.startswith(("✗ ", "⊘ ", "!! ", "xx ")):
        style = RED
    elif body.startswith(("? ", "WAITING FOR YOU")):
        style = f"bold {MAGENTA}"
    elif body.startswith("⚠"):
        style = YELLOW
    elif body.startswith("❯"):
        style = f"bold {CYAN}"
    return hanging(text, style=style, hang=0 if body.startswith("ahohs ") else 2)       # a command to copy wraps without an indent put into it


class PolishedApp(App):
    """The screen. ``press`` is attached by the driver while a run is attended and ``None`` between runs."""

    CSS = """
    Screen { background: $surface; }
    #head { height: 1; padding: 0 1; background: $panel; color: $text; text-style: bold; }
    #transcript { height: 1fr; width: 100%; padding: 0 1; scrollbar-size-vertical: 1; overflow-x: hidden; scrollbar-color: #5f87d7; scrollbar-background: #121212; }
    #work { height: auto; max-height: 14; border-left: thick $warning 60%; padding: 0 1; margin: 0 1; color: $text-muted; overflow: hidden hidden; }
    #detail { height: 2fr; border-left: thick $warning 80%; border-top: dashed $warning 60%; padding: 0 1; margin: 0 1; color: $text-muted; scrollbar-size-vertical: 1; scrollbar-color: #5f87d7; scrollbar-background: #121212; }
    #detail-body { height: auto; }
    #bottom-bar { dock: bottom; height: auto; }
    #activity { height: 1; padding: 0 1; margin: 0 1; }
    #command-menu { height: auto; max-height: 14; margin: 0 1; border: none; background: $panel; display: none; }
    #prompt { margin: 0 1; border: tall $accent 60%; background: $panel; height: 3; max-height: 10; }
    #prompt:focus { border: tall $accent; }
    #prompt .text-area--placeholder { color: $text-muted; }
    #prompt.-awaiting .text-area--placeholder { color: $warning; }
    #keys { height: 1; padding: 0 1; background: $panel; }
    """

    BINDINGS = [
        Binding("ctrl+c", "copy_or_quit", "Quit", priority=True),
        Binding("ctrl+d", "eof", "Leave", priority=True),
        Binding("escape", "stop", "Stop"),
        Binding("ctrl+l", "clear_log", "Clear screen"),
        Binding("alt+y", "copy_last", "Copy last reply"),      # not Ctrl+Y: the prompt's own binding for it (redo) answers first
        Binding("alt+d", "toggle_detail", "Details"),
        Binding("alt+t", "toggle_structure", "Structure"),
        Binding("alt+k", "continue_stopped", "Resume"),
        Binding("tab", "tab", "Next run", priority=True),      # priority: the screen's own Tab (focus next) would otherwise answer first
        Binding("pageup", "scroll_up_or_run", "Scroll up", priority=True),
        Binding("pagedown", "scroll_down_or_run", "Scroll down", priority=True),
    ]

    def __init__(self, *, title: str = "", commands: Optional[Mapping[str, Callable[..., Any]]] = None, choices: Optional[menu_module.Choices] = None,
                 log_prefixes: Sequence[str] = ("hubofhubs",), log_path: Any = None, verbosity: int = 0, environ: Optional[Mapping[str, str]] = None) -> None:
        super().__init__()
        self.title = title or say("polished.screen.title")
        self.env = dict(environ or {})        # the environment the entry point handed in; the screen never reads the process environment
        self.press: Optional[Callable[..., None]] = None
        self.attendance: Any = None
        self.start_hook: Callable[[], None] = lambda: None
        self.lines: "queue.Queue[Optional[str]]" = queue.Queue()
        self.history: List[str] = []
        self.position = 0
        self.reading = False
        self.ended = False
        self.drawing: "queue.Queue[Any]" = queue.Queue()
        self.ui_thread = 0
        self.snap = Snapshot()
        self.active = ""                       # the run the detail opens
        self.quit_armed_until = 0.0
        self.quit_requested = False
        self.stop_announced = False
        self.last_reply = ""
        self.commands = menu_module.builtin_commands() + menu_module.custom_commands(commands or {})
        self.choices = choices
        self.shown_items: List[menu_module.MenuItem] = []
        self.shown_prompt = ""
        self.log_args = (tuple(log_prefixes), log_path, verbosity)
        self.folder: Optional[NoticeFolder] = None
        self.detached: List[logging.Handler] = []
        self.root_level: Optional[int] = None

    # --- layout ---------------------------------------------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static("", id="head")
        yield TranscriptLog(id="transcript", max_lines=20000, wrap=True, min_width=1, highlight=False, markup=False, auto_scroll=True)
        yield WorkPanel(id="work")
        yield DetailPanel(id="detail")
        with Vertical(id="bottom-bar"):
            yield ActivityBar(id="activity")
            yield OptionList(id="command-menu")
            yield PromptBox(id="prompt", soft_wrap=True, tab_behavior="focus", show_line_numbers=False, compact=True, placeholder=words_of.placeholder("ready", self.env))
            yield KeyHints(id="keys")

    def on_mount(self) -> None:
        self.ui_thread = threading.get_ident()
        self.tlog = self.query_one("#transcript", TranscriptLog)
        self.work_panel = self.query_one("#work", WorkPanel)
        self.detail = self.query_one("#detail", DetailPanel)
        self.activity = self.query_one("#activity", ActivityBar)
        self.prompt_box = self.query_one("#prompt", PromptBox)
        self.activity.transcript = self.tlog
        self.query_one("#head", Static).update(Text(self.title))
        self.prompt_box.focus()
        prefixes, path, verbosity = self.log_args
        self.folder = NoticeFolder(self.add_line, self.schedule, verbosity=verbosity, log_path=path, own=prefixes, environ=self.env)
        root = logging.getLogger()
        self.detached = [h for h in root.handlers if type(h) is logging.StreamHandler]     # a handler that writes to the terminal would draw over the screen
        for handler in self.detached:
            root.removeHandler(handler)
        root.addHandler(self.folder)
        self.root_level = root.level
        if root.level == logging.NOTSET or root.level > logging.WARNING:
            root.setLevel(logging.WARNING if verbosity < 1 else logging.INFO)
        threading.Thread(target=self.pump, daemon=True).start()
        self.start_hook()

    def on_unmount(self) -> None:
        self.ended = True
        self.drawing.put(None)
        self.lines.put(None)
        root = logging.getLogger()
        if self.folder is not None:
            root.removeHandler(self.folder)
            self.folder.close()
        for handler in self.detached:
            root.addHandler(handler)
        if self.root_level is not None:
            root.setLevel(self.root_level)

    # --- drawing from the driver's thread -----------------------------------------------------------------------------------------

    def on_ui_thread(self) -> bool:
        return threading.get_ident() == self.ui_thread

    def post(self, function: Callable[..., None], *args: Any) -> None:
        """Hand a drawing call to the screen without making the driver wait for it: a pump thread applies them in order (directly, on the screen's own thread)."""
        if self.ended:
            return
        if self.on_ui_thread():
            function(*args)
        else:
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

    def schedule(self, delay: float, function: Callable[[], None]) -> None:
        self.post(lambda: self.set_timer(delay, function))

    def add_line(self, text: str) -> None:
        self.post(self.write_text, style_line(text))

    def add_ansi(self, text: str) -> None:
        self.post(self.write_text, Text.from_ansi(text) if "\x1b" in text else hanging(text, hang=2))

    def write_text(self, text: Text) -> None:
        self.tlog.write(text)

    def add_markdown(self, text: str) -> None:
        self.last_reply = text.strip()
        self.post(lambda: self.tlog.write(Markdown(text)))

    def begin_run(self) -> None:
        if self.folder is not None:
            self.folder.begin_run()

    def apply_snapshot(self, snap: Snapshot) -> None:
        self.snap = snap
        self.query_one("#head", Static).update(Text(snap.head))
        self.activity.display = snap.busy
        if snap.busy:
            self.activity.set_status(snap.activity)
            self.activity.set_wait(snap.waited)
            self.activity.set_queued(snap.queued)
        else:
            self.activity.set_queued(0)
        runs = [run for run, _ in snap.runs]
        if self.active not in runs:
            self.active = runs[0] if runs else ""
        rows, line_map = self.rows_with_active(snap)
        self.work_panel.show(rows, line_map)
        if self.detail.display:
            if self.detail.run_id in runs:
                self.fill_detail(self.detail.run_id, update=True)
            else:
                self.detail.close()
        state = snap.prompt
        if state != self.shown_prompt:
            self.shown_prompt = state
            self.prompt_box.placeholder = words_of.placeholder(state, self.env)
            self.prompt_box.set_class(state == "asking", "-awaiting")

    def rows_with_active(self, snap: Snapshot) -> Tuple[List[Tuple[str, str]], Dict[int, str]]:
        """The panel's rows with the open run's header marked (the driver does not know which run the person opened)."""
        if not self.detail.display:
            return snap.rows, snap.line_map
        out = []
        for index, (row, kind) in enumerate(snap.rows):
            if kind in ("head", "open") and snap.line_map.get(index) == self.detail.run_id:
                out.append(("▾" + row[1:], "open"))
            elif kind == "open":
                out.append(("▸" + row[1:], "head"))
            else:
                out.append((row, kind))
        return out, snap.line_map

    # --- the detail panel -------------------------------------------------------------------------------------------------------

    def fill_detail(self, run_id: str, update: bool = False) -> None:
        runs = self.snap.runs
        ids = [r for r, _ in runs]
        title = dict(runs).get(run_id, "")
        lines = self.snap.histories.get(run_id, [])
        extra = self.snap.metrics if run_id == (ids[0] if ids else "") else []
        position = ids.index(run_id) + 1 if run_id in ids else 1
        if update:
            self.detail.update_content(title, lines, position, len(ids), extra)
        else:
            self.detail.open_for(run_id, title, lines, position, len(ids), extra)

    def toggle_detail(self, run_id: str = "") -> None:
        run_id = run_id or self.active or (self.snap.runs[0][0] if self.snap.runs else "")
        if self.detail.display and (not run_id or self.detail.run_id == run_id):
            self.detail.close()
            self.apply_snapshot(self.snap)
            return
        if not run_id:
            return
        self.active = run_id
        self.fill_detail(run_id)
        self.apply_snapshot(self.snap)

    def action_toggle_detail(self) -> None:
        self.toggle_detail()

    def action_toggle_structure(self) -> None:
        if self.press is not None:
            self.press("tree")

    def cycle_run(self) -> None:
        ids = [r for r, _ in self.snap.runs]
        if len(ids) < 2:
            return
        current = self.detail.run_id if self.detail.display else self.active
        self.active = ids[(ids.index(current) + 1) % len(ids)] if current in ids else ids[0]
        if self.detail.display:
            self.fill_detail(self.active)
        self.apply_snapshot(self.snap)

    # --- reading a line at the prompt (between runs) ----------------------------------------------------------------------------

    def read(self, prompt: str) -> Optional[str]:
        self.reading = True
        self.post(setattr, self.prompt_box, "placeholder", words_of.placeholder("ready", self.env))
        try:
            return self.lines.get()
        finally:
            self.reading = False

    def set_prompt_text(self, text: str) -> None:
        """Put text in the prompt after whatever the person has typed there (nothing of theirs is replaced)."""
        def put() -> None:
            typed = self.prompt_box.text.rstrip()
            self.prompt_box.text = f"{typed}\n\n{text}" if typed else text
            self.prompt_box.move_cursor(self.prompt_box.document.end)
        self.post(put)

    # --- keys -------------------------------------------------------------------------------------------------------------------

    def send(self, token: str, text: str = "") -> None:
        if self.press is not None:
            self.press(token, text)

    def action_stop(self) -> None:
        if self.snap.busy:
            self.send("esc")

    def action_continue_stopped(self) -> None:
        if self.snap.stopped:
            self.send("line", "resume")

    def action_eof(self) -> None:
        self.request_quit()

    def request_quit(self) -> None:
        """Leave: stop the run and keep its session, end the prompt's read, and close once the run has stopped (or after a short grace)."""
        self.quit_requested = True
        self.send("eof")
        self.lines.put(None)
        self.set_timer(QUIT_GRACE_SECONDS, self.exit)

    def action_tab(self) -> None:
        if self.command_menu_key("tab"):
            return
        self.cycle_run()

    def action_clear_log(self) -> None:
        self.tlog.clear()

    def action_scroll_up_or_run(self) -> None:
        self.detail.page_back() if self.detail.display else self.tlog.scroll_page_up(animate=False)

    def action_scroll_down_or_run(self) -> None:
        self.detail.page_forward() if self.detail.display else self.tlog.scroll_page_down(animate=False)

    def on_mouse_scroll_up(self, event: Any) -> None:
        event.stop()
        target = self.detail if self.detail.display else self.tlog
        if target is self.detail:
            self.detail.follow = False
        target.scroll_to(y=max(0, target.scroll_target_y - self.scroll_sensitivity_y), animate=False)

    def on_mouse_scroll_down(self, event: Any) -> None:
        event.stop()
        target = self.detail if self.detail.display else self.tlog
        target.scroll_to(y=target.scroll_target_y + self.scroll_sensitivity_y, animate=False)
        if target is self.detail and self.detail.scroll_y >= self.detail.max_scroll_y - 1:
            self.detail.follow = True

    def key_hints(self) -> List[Tuple[str, str]]:
        """The keys worth showing now (see ``text.key_hints``)."""
        snap = self.snap
        return words_of.key_hints(busy=snap.busy, asking=snap.asking, stopped=snap.stopped, runs=len(snap.runs), detail=self.detail.display, structure=snap.structure,
                                  agents=snap.agents_nav, inside=snap.inside)

    # --- copy, stop, or ask twice to quit ---------------------------------------------------------------------------------------------

    def emit_osc52(self, text: str) -> bool:
        """Write an OSC-52 clipboard sequence to the terminal (best effort, wrapped for tmux), so copy works over a remote shell with no clipboard program."""
        driver = getattr(self, "_driver", None)
        if driver is None:
            return False
        try:
            sequence = f"\x1b]52;c;{base64.b64encode(text.encode('utf-8')).decode('ascii')}\x07"
            if self.env.get("TMUX"):
                sequence = "\x1bPtmux;" + sequence.replace("\x1b", "\x1b\x1b") + "\x1b\\"
            driver.write(sequence)
            return True
        except Exception:  # noqa: BLE001
            return False

    def copy_text(self, text: str) -> Tuple[bool, str]:
        tool_ok, why = copy_with_tool(text)
        osc_ok = self.emit_osc52(text)
        if tool_ok:
            return True, say("polished.copy.clipboard")
        if osc_ok:
            return True, say("polished.copy.sent")
        return False, why.strip("()")

    def action_copy_last(self) -> None:
        if not self.last_reply:
            self.notify(say("polished.copy.nothing"), title=say("polished.copy.title"), timeout=2, severity="warning")
            return
        ok, detail = self.copy_text(self.last_reply)
        self.notify(say("polished.copy.last", detail=detail), title=say("polished.copy.titleDone" if ok else "polished.copy.title"), timeout=2.5, severity="information" if ok else "warning")

    def selected(self) -> str:
        found = self.tlog.selected_text
        if found.strip():
            return found
        try:
            return self.screen.get_selected_text() or ""
        except Exception:  # noqa: BLE001
            return ""

    def action_copy_or_quit(self) -> None:
        """Ctrl+C: copy the selected text if there is any; otherwise stop the work (or, idle, say so), and a second press within three seconds quits. One press never ends the app."""
        selection = self.selected()
        if selection.strip():
            self.copy_text(selection)
            self.tlog.clear_selection()
            preview = " ".join(selection.split())
            preview = (preview[:60] + "…") if len(preview) > 60 else preview
            self.write_text(hanging("  " + say("polished.ctrlc.copied", preview=preview), DIM))
            return
        now = time.monotonic()
        if now < self.quit_armed_until:
            self.request_quit()
            return
        self.quit_armed_until = now + QUIT_CONFIRM_SECONDS
        if self.snap.busy:
            self.action_stop()
            self.stop_announced = True
            self.write_text(hanging("  " + say("polished.ctrlc.stopped"), DIM))
        else:
            self.write_text(hanging("  " + say("polished.ctrlc.idle"), DIM))

    def on_transcript_log_copied(self, event: Any) -> None:
        ok, detail = self.copy_text(event.text)
        self.notify(say("polished.copy.selection", count=len(event.text), detail=detail), title=say("polished.copy.titleDone" if ok else "polished.copy.title"), timeout=2.5,
                    severity="information" if ok else "warning")

    def on_transcript_log_clicked(self, event: Any) -> None:
        self.prompt_box.focus()

    def on_click(self, event: Any) -> None:
        """A click anywhere leaves the cursor in the prompt; a drag selection is not cleared by the focus change and Ctrl+C still copies it."""
        try:
            box = self.query_one("#prompt", PromptBox)
        except Exception:  # noqa: BLE001
            return
        if self.focused is not box:
            box.focus()

    # --- the prompt: submit, history, the menu, one-key answers ------------------------------------------------------------------------

    def on_prompt_box_submitted(self, event: PromptBox.Submitted) -> None:
        line = (event.value or "").strip()
        event.box.clear()
        event.box.styles.height = 3
        self.close_menu()
        if not line:
            return
        self.tlog.follow_now()
        if line == "/clear":
            self.tlog.clear()
            self.write_text(hanging("  " + say("polished.screen.cleared"), DIM))
            return
        self.history.append(line)
        self.position = len(self.history)
        if self.press is not None:
            self.send("line", line)
        else:
            self.lines.put(line)

    def history_key(self, key: str) -> bool:
        box = self.prompt_box
        if key not in ("up", "down") or not self.history or self.menu().display:
            return False
        row = box.cursor_location[0]
        last = box.document.line_count - 1
        if (key == "up" and row != 0) or (key == "down" and row != last):
            return False
        self.position = max(0, min(self.position + (-1 if key == "up" else 1), len(self.history)))
        box.text = self.history[self.position] if self.position < len(self.history) else ""
        box.move_cursor(box.document.end)
        return True

    def answer_key(self, key: str) -> bool:
        """A question is open and the prompt is empty: one key answers it."""
        if self.snap.asking and key in ("y", "n") and not self.prompt_box.text:
            self.send("line", key)
            return True
        return False

    def tree_key(self, key: str) -> bool:
        """With the structure open and nothing typed, the arrows move in it (otherwise they move the cursor)."""
        token = {"up": "up", "down": "down", "right": "open", "left": "close"}.get(key)
        if token and (self.snap.structure_open or self.snap.agents_nav) and not self.prompt_box.text and self.press is not None:
            self.send(token)
            return True
        return False

    def menu(self) -> OptionList:
        return self.query_one("#command-menu", OptionList)

    def close_menu(self) -> None:
        try:
            menu = self.menu()
        except Exception:  # noqa: BLE001
            return
        menu.display = False
        self.shown_items = []

    def on_text_area_changed(self, event: Any) -> None:
        if getattr(event.text_area, "id", None) == "prompt":
            self.refresh_menu()

    def refresh_menu(self) -> None:
        menu = self.menu()
        items = menu_module.menu_items(self.prompt_box.text, self.commands, self.choices)
        self.shown_items = items
        menu.clear_options()
        if not items:
            menu.display = False
            return
        width = min(max(len(i.label) for i in items), 60) + 2
        menu.add_options([Option(Text.assemble((i.label.ljust(width), "bold"), (i.description, ""))) for i in items])
        menu.highlighted = 0
        menu.display = True

    def command_menu_key(self, key: str) -> bool:
        """A key while the menu is open: arrows move, Tab completes, Enter runs a complete command, Esc closes. True when the menu used it."""
        try:
            menu = self.menu()
        except Exception:  # noqa: BLE001
            return False
        if not menu.display or not self.shown_items:
            return False
        count = len(self.shown_items)
        current = menu.highlighted if menu.highlighted is not None else 0
        if key == "up":
            menu.highlighted = (current - 1) % count
            return True
        if key == "down":
            menu.highlighted = (current + 1) % count
            return True
        if key == "escape":
            self.close_menu()
            return True
        if key not in ("tab", "enter"):
            return False
        item = self.shown_items[current]
        if key == "enter" and item.submit:
            self.prompt_box.post_message(PromptBox.Submitted(self.prompt_box, item.completion))
            self.close_menu()
            return True
        self.prompt_box.text = item.completion
        self.prompt_box.move_cursor(self.prompt_box.document.end)
        return True


class Transcript:
    """The text stream a session writes to: each finished line goes to the screen and into a buffer the caller's ``out`` receives at the end."""

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
        """A line for the buffer only (the screen drew it another way)."""
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


__all__ = ["AppKeys", "PolishedApp", "Snapshot", "Transcript", "copy_with_tool", "style_line"]
