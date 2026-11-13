"""The widgets of the polished screen (Textual, MIT licence; imported only when the screen is built).

``HangingText`` (a wrapped row starts under its words, not under its marker), ``TranscriptLog`` (follows the tail until the person scrolls away, and drag-to-select with copy),
``ActivityBar`` (one live row: dots, the clock once a wait passes three seconds, the status, the count of notes waiting), ``WorkPanel`` (the calm per-run block, click a run to open it),
``DetailPanel`` (one run's full history with a follow toggle), ``KeyHints`` (the keys that do something now, whole hints only) and ``PromptBox`` (a multi-line prompt docked at the bottom
that submits on Enter). They know no harness and no consumer: the app feeds them plain text.
"""
from __future__ import annotations

import enum
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import text as words_of
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import say

def load_libraries() -> None:
    """Bind the Textual and Rich names this module's classes are built on. The imports are inside a function, as the import boundary requires of every library of an extra
    (``tests/test_import_boundary.py``); this module is itself imported only when the screen is built (``session.py`` imports it inside a function), so nothing needs the extra before then."""
    from rich.segment import Segment
    from rich.style import Style as RichStyle
    from rich.text import Text
    from textual._ansi_sequences import ANSI_SEQUENCES_KEYS
    from textual.app import ComposeResult
    from textual.containers import VerticalScroll
    from textual.geometry import Offset
    from textual.message import Message
    from textual.selection import Selection
    from textual.strip import Strip
    from textual.widgets import RichLog, Static, TextArea
    globals().update(Segment=Segment, RichStyle=RichStyle, Text=Text, ANSI_SEQUENCES_KEYS=ANSI_SEQUENCES_KEYS, ComposeResult=ComposeResult, VerticalScroll=VerticalScroll,
                     Offset=Offset, Message=Message, Selection=Selection, Strip=Strip, RichLog=RichLog, Static=Static, TextArea=TextArea)


load_libraries()

# The colours of text that carries information, each at least 4.5:1 against the dark theme's surfaces (the screen's contrast test measures every state).
GREEN, RED, MAGENTA, YELLOW, CYAN, DIM = "#5fd75f", "#ff6b6b", "#ff87ff", "#ffd75f", "#5fd7ff", "#a8a8a8"
HANG_DEFAULT = 2
HANG_MIN_BODY = 8         # a line is not wrapped with a hanging indent in a terminal narrower than the indent plus this
STATUS_WIDTH_FALLBACK = 76
STATUS_MIN_CHARS = 12


class HangingText(Text):
    """A transcript line whose wrapped rows start under its words, not under its marker. The transcript wraps it (``rows``) before writing; anywhere else it is a ``Text``."""

    def __init__(self, *args: Any, hang: int = HANG_DEFAULT, carry: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.hang, self.carry = hang, carry

    def copy(self) -> "HangingText":
        clone = HangingText(self.plain, style=self.style, justify=self.justify, overflow=self.overflow, no_wrap=self.no_wrap, end=self.end, tab_size=self.tab_size,
                            hang=self.hang, carry=self.carry)
        clone._spans[:] = self._spans
        return clone

    def rows(self, width: int, console: Any) -> List[Text]:
        hang = self.hang
        if width < hang + HANG_MIN_BODY or hang <= 0:
            return [self]
        out: List[Text] = []
        first: Optional[Text] = None
        for paragraph in self.split("\n", allow_blank=True):
            if first is None:
                first = paragraph[:hang]
                prefix, body = first, paragraph[hang:]
            else:
                prefix, body = (first if self.carry else Text(" " * hang, style=first.style)), paragraph
            pieces = body.wrap(console, width - hang)
            if not pieces:
                out.append(prefix.copy())
                continue
            for index, piece in enumerate(pieces):
                row = prefix.copy() if index == 0 or self.carry else Text(" " * hang, style=prefix.style)
                row.append_text(piece)
                out.append(row)
        return out


def hanging(text: str, style: str = "", hang: int = HANG_DEFAULT, carry: bool = False) -> HangingText:
    return HangingText(text, style=style, hang=hang, carry=carry)


# --- the transcript ---------------------------------------------------------------------------------------------------------------------

class TranscriptLog(RichLog):
    """A ``RichLog`` that follows the tail only while the person has not scrolled away from it, and selects text by dragging.

    Following is a state, not a measurement of the view (the view changes size without a touch when the work panel appears). A stock log paints no selection, so the selection
    is kept here in content coordinates, painted in ``render_line`` and copied on release (a message the app turns into the clipboard write)."""

    can_focus = False      # clicking the transcript never takes the keyboard from the prompt

    class Copied(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class Clicked(Message):
        """A plain click (press and release, no drag): the app puts the cursor back in the prompt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sel_from: Optional[Offset] = None
        self.sel_to: Optional[Offset] = None
        self.dragging = False
        self.following = True
        self.unseen_below = False       # something was written while the view was not following

    def write(self, content: Any, width: Optional[int] = None, expand: bool = False, shrink: bool = True, scroll_end: Optional[bool] = None, animate: bool = False) -> Any:
        if scroll_end is None and self.auto_scroll:
            scroll_end = self.following
        if not self.following and not (isinstance(content, Text) and not content.plain.strip()):
            self.unseen_below = True
        if isinstance(content, HangingText) and width is None and self._size_known:
            for row in content.rows(self.scrollable_content_region.width, self.app.console):
                super().write(row, width=width, expand=expand, shrink=shrink, scroll_end=scroll_end, animate=animate)
            return self
        return super().write(content, width=width, expand=expand, shrink=shrink, scroll_end=scroll_end, animate=animate)

    def clear(self) -> "TranscriptLog":
        """Empty the log; an empty log is at its bottom, so it follows again."""
        super().clear()
        self.following, self.unseen_below = True, False
        return self

    def follow_now(self) -> None:
        """Go to the newest output and follow it again (the person sent a message, or the run ended)."""
        self.following, self.unseen_below = True, False
        self.scroll_end(animate=False, immediate=False, x_axis=False)

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        self.following = new_value >= self.max_scroll_y - 1
        if self.following:
            self.unseen_below = False

    def on_resize(self, event: Any) -> None:
        if self.following and self._size_known:
            self.scroll_end(animate=False, immediate=False, x_axis=False)

    # -- drag selection --

    def offset_of(self, event: Any) -> Offset:
        scroll_x, scroll_y = self.scroll_offset
        x = max(0, int(getattr(event, "x", 0)) + scroll_x)
        y = max(0, int(getattr(event, "y", 0)) + scroll_y)
        if self.lines:
            y = min(y, len(self.lines) - 1)
        return Offset(x, y)

    def on_mouse_down(self, event: Any) -> None:
        if getattr(event, "button", 1) not in (0, 1):
            return
        self.capture_mouse(True)
        self.dragging = True
        self.sel_from = self.sel_to = self.offset_of(event)
        self.refresh()
        event.stop()

    def on_mouse_move(self, event: Any) -> None:
        if not self.dragging:
            return
        self.sel_to = self.offset_of(event)
        try:
            height = self.scrollable_content_region.height
        except Exception:  # noqa: BLE001
            height = self.size.height
        if getattr(event, "y", 0) < 0:
            self.scroll_up(animate=False)
        elif getattr(event, "y", 0) >= height:
            self.scroll_down(animate=False)
        self.refresh()
        event.stop()

    def on_mouse_up(self, event: Any) -> None:
        if not self.dragging:
            return
        self.dragging = False
        self.release_mouse()
        text = self.selected_text
        if text:
            self.post_message(self.Copied(text))
        else:
            self.clear_selection()
            self.post_message(self.Clicked())
        event.stop()

    def clear_selection(self) -> None:
        if self.sel_from is not None or self.sel_to is not None:
            self.sel_from = self.sel_to = None
            self.refresh()

    def chosen(self) -> Optional[Selection]:
        if self.sel_from is None or self.sel_to is None or self.sel_from == self.sel_to:
            return None
        return Selection.from_offsets(self.sel_from, self.sel_to)

    @property
    def selected_text(self) -> str:
        found = self.chosen()
        return "" if found is None else self.extract([s.text for s in self.lines], found)

    @staticmethod
    def extract(line_texts: List[str], found: Selection) -> str:
        """The selected text from the log's per-row text, with each row's trailing padding trimmed and its line breaks kept."""
        raw = found.extract("\n".join(line_texts))
        return "\n".join(part.rstrip() for part in raw.split("\n")).strip("\n")

    def paint_style(self) -> RichStyle:
        """The theme's selection background only, so each cell keeps its own foreground and stays readable; reverse video when the theme has none."""
        try:
            themed = self.selection_style      # the ``screen--selection`` component, resolved by the widget
        except Exception:  # noqa: BLE001
            themed = None
        if themed is not None and themed.bgcolor is not None:
            return RichStyle(bgcolor=themed.bgcolor)
        return RichStyle(reverse=True)

    @staticmethod
    def highlight(strip: Strip, a: int, b: int, style: RichStyle) -> Strip:
        """``strip`` with cells [a, b) restyled: the highlight laid over each cell's own style, so the selection background wins and the text keeps its colour."""
        length = strip.cell_length
        a = max(0, min(a, length))
        b = max(a, min(b, length))
        if a >= b:
            return strip
        parts = list(strip.divide([a, b, length]))
        if len(parts) < 2:
            return strip
        left, mid, *rest = parts
        lit = Strip([Segment(seg.text, (seg.style + style) if seg.style else style, seg.control) for seg in mid._segments], mid.cell_length)
        return Strip.join([left, lit, *rest])

    def render_line(self, y: int) -> Strip:
        strip = super().render_line(y)
        found = self.chosen()
        if found is None:
            return strip
        scroll_x, scroll_y = self.scroll_offset
        span = found.get_span(scroll_y + y)
        if span is None:
            return strip
        x0, x1 = span
        length = strip.cell_length
        return self.highlight(strip, x0 - scroll_x, length if x1 == -1 else x1 - scroll_x, self.paint_style())


# --- the live rows --------------------------------------------------------------------------------------------------------------------

class ActivityBar(Static):
    """Three animated dots, the clock, the status and the count of notes waiting, in one line.

    The clock runs from the start of the run (a status change does not reset it) and shows only once a wait passes ``CLOCK_AFTER`` seconds, so a long silent step never looks frozen
    and an instant one has no counter. It stands before the status text, and the text is cut to the room left, so a long status never pushes the clock or the count off a narrow
    terminal. The app feeds the elapsed seconds (the session's own clock) with each snapshot."""

    INTERVAL = 0.45

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.status = say("polished.activity.working")
        self.frame = 0
        self.waited: Optional[float] = None
        self.queued = 0
        self.transcript: Any = None
        self.display = False

    def on_mount(self) -> None:
        self.set_interval(self.INTERVAL, self.tick)

    def tick(self) -> None:
        self.frame = (self.frame + 1) % 3
        self.refresh()

    def set_status(self, text: str) -> None:
        self.status = text[:1].upper() + text[1:]
        self.refresh()

    def set_wait(self, seconds: Optional[float]) -> None:
        self.waited = seconds
        self.refresh()

    def set_queued(self, count: int) -> None:
        self.queued = count
        self.refresh()

    def shown_clock(self) -> Optional[str]:
        if self.waited is None or int(self.waited) < words_of.CLOCK_AFTER:
            return None
        return words_of.clock(self.waited)

    def render(self) -> Text:
        t = Text()
        for index in range(3):
            if index:
                t.append(" ")
            t.append("●", style="cyan bold" if index == self.frame else "cyan")
        t.append("  ")
        shown = self.shown_clock()
        if shown is not None:
            t.append(shown + "  ")
        waiting = f"  · {say('polished.activity.waitingNotes', count=self.queued)}" if self.queued else ""
        below = f"  {say('polished.activity.newBelow')}" if getattr(self.transcript, "unseen_below", False) else ""
        room = (self.size.width or STATUS_WIDTH_FALLBACK) - len(t.plain) - len(waiting) - len(below)
        t.append(words_of.ellipsize(self.status, max(room, STATUS_MIN_CHARS)))
        if waiting:
            t.append(waiting, style=f"bold {YELLOW}")
        if below:
            t.append(below, style=f"bold {YELLOW}")
        return t


KIND_STYLE = {"head": f"bold {CYAN}", "open": f"bold {YELLOW}", "clock": "", "step": "", "hint": ""}


class WorkPanel(Static):
    """The calm block of what is running now, updated in place. Click a run's rows to open its detail."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rows: List[Tuple[str, str]] = []
        self.line_map: Dict[int, str] = {}
        self.display = False

    def show(self, rows: Sequence[Tuple[str, str]], line_map: Optional[Dict[int, str]] = None) -> None:
        self.rows, self.line_map = list(rows), dict(line_map or {})
        self.display = bool(self.rows)
        self.refresh(layout=True)      # as tall as its text: a new height needs a new layout, not only a repaint

    def hide(self) -> None:
        self.show([], {})

    def render(self) -> Text:
        t = Text(no_wrap=False)
        for index, (row, kind) in enumerate(self.rows):
            t.append(row + ("\n" if index < len(self.rows) - 1 else ""), style=KIND_STYLE.get(kind, ""))
        return t

    def on_click(self, event: Any) -> None:
        run_id = self.line_map.get(event.y)
        if run_id is None:
            return
        event.stop()
        self.app.toggle_detail(run_id)


class DetailPanel(VerticalScroll):
    """One run's full history, hidden until asked (Alt+D). It follows the newest step until the person scrolls back (PgUp, the wheel), and follows again at the end."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.run_id: Optional[str] = None
        self.title = ""
        self.lines: List[str] = []
        self.extra: List[str] = []
        self.position, self.total = 1, 1
        self.follow = True
        self.display = False
        self.body = Static(id="detail-body")

    def compose(self) -> ComposeResult:
        yield self.body

    def open_for(self, run_id: str, title: str, lines: Sequence[str], position: int = 1, total: int = 1, extra: Sequence[str] = ()) -> None:
        self.run_id, self.follow, self.display = run_id, True, True
        self.update_content(title, lines, position, total, extra)

    def update_content(self, title: str, lines: Sequence[str], position: int = 1, total: int = 1, extra: Sequence[str] = ()) -> None:
        self.title, self.lines, self.extra, self.position, self.total = title, list(lines), list(extra), position, total
        self.rerender()

    def close(self) -> None:
        self.run_id, self.display = None, False
        self.rerender()

    def page_back(self) -> None:
        self.follow = False
        self.scroll_page_up(animate=False)

    def page_forward(self) -> None:
        self.scroll_page_down(animate=False)
        if self.scroll_offset.y >= self.max_scroll_y - 1:
            self.follow = True

    def on_mouse_scroll_up(self, event: Any) -> None:
        self.follow = False

    def on_mouse_scroll_down(self, event: Any) -> None:
        def check() -> None:
            if self.scroll_y >= self.max_scroll_y - 1:
                self.follow = True
        self.call_after_refresh(check)

    def text(self) -> Text:
        if not self.run_id:
            return Text("")
        head = say("polished.work.detailTitleMany", position=self.position, total=self.total, title=words_of.ellipsize(self.title, 60)) if self.total > 1 \
            else say("polished.work.detailTitle", title=words_of.ellipsize(self.title, 60))
        t = Text(no_wrap=False)
        t.append(head + "\n", style=f"bold {CYAN}")
        t.append("\n".join(f"  {line}" for line in self.lines) + "\n")
        if self.extra:
            t.append("\n  " + say("polished.work.metrics") + "\n", style="bold")
            t.append("\n".join(f"  {row}" for row in self.extra) + "\n")
        t.append("  " + say("polished.work.detailNavMany" if self.total > 1 else "polished.work.detailNav"))
        t.append("  (" + say("polished.work.detailFollowing" if self.follow else "polished.work.detailPaused") + ")")
        return t

    def rerender(self) -> None:
        self.body.update(self.text())
        if self.follow and self.run_id:
            self.call_after_refresh(self.scroll_end, animate=False)


class KeyHints(Static):
    """The one line of keys that do something right now, under the prompt: as many whole hints as fit, never a key cut in half."""

    def on_mount(self) -> None:
        self.set_interval(0.5, self.refresh)

    def render(self) -> Text:
        variables = self.app.get_css_variables()
        key_style = f"bold {variables.get('footer-key-foreground', '#FFA62B')}"
        label_style = variables.get("footer-description-foreground", "#E0E0E0")
        room = self.size.width or STATUS_WIDTH_FALLBACK
        t = Text(no_wrap=True, overflow="crop")
        try:
            hints = words_of.fit_hints(self.app.key_hints(), room)
        except AttributeError:      # painted before the app finished mounting
            hints = []
        for key, label in hints:
            if t.plain:
                t.append("  ")
            t.append(words_of.present.key_name(key), style=key_style)
            t.append(f" {label}", style=label_style)
        return t


# --- the prompt ---------------------------------------------------------------------------------------------------------------------------

ALT_ENTER = "\x1b\r"
PromptKeys = enum.Enum("PromptKeys", {"AltEnter": "alt+enter"})
# Textual reads ESC CR as a bare Enter and loses the Alt, so Alt+Enter would submit; registering the whole sequence makes it a newline key.
ANSI_SEQUENCES_KEYS.setdefault(ALT_ENTER, (PromptKeys.AltEnter,))


class PromptBox(TextArea):
    """A multi-line prompt that grows with its text. Enter submits. A newline comes from Shift+Enter (where the terminal can tell it from Enter), Alt+Enter, Ctrl+J, or a
    backslash typed right before Enter (the trailing line feed of that keypress is dropped)."""

    class Submitted(Message):
        def __init__(self, box: "PromptBox", value: str) -> None:
            super().__init__()
            self.box, self.value = box, value

    MAX_LINES = 8
    PAIRED_LF_WINDOW = 0.05
    backslash_at: float = 0.0

    def on_key(self, event: Any) -> None:
        key = event.key
        for hook in ("command_menu_key", "answer_key", "tree_key", "history_key"):
            use = getattr(self.app, hook, None)
            if use is not None and use(key):
                event.prevent_default()
                event.stop()
                return
        if key.startswith("alt+") and key != "alt+enter" and len(key) == 5:
            event.prevent_default()      # the app's own Alt bindings must see Alt+letter, not the text box typing the letter
            self.backslash_at = 0.0
            return
        if key == "enter":
            event.prevent_default()
            event.stop()
            if self.eat_backslash():
                self.insert("\n")
                self.backslash_at = event.time
                return
            self.post_message(self.Submitted(self, self.text))
        elif key in ("shift+enter", "alt+enter", "ctrl+j"):
            event.prevent_default()
            event.stop()
            paired = key == "ctrl+j" and event.time - self.backslash_at < self.PAIRED_LF_WINDOW
            self.backslash_at = 0.0
            if not paired:
                self.insert("\n")
        else:
            self.backslash_at = 0.0

    def eat_backslash(self) -> bool:
        if not self.selection.is_empty:
            return False
        row, col = self.cursor_location
        if col == 0 or self.document[row][col - 1] != "\\":
            return False
        self.delete((row, col - 1), (row, col))
        return True

    def on_text_area_changed(self, event: Any) -> None:
        self.fit_height()

    def on_resize(self, event: Any) -> None:
        self.call_after_refresh(self.fit_height)

    def fit_height(self) -> None:
        """Show every row the text occupies, wrapped rows included, up to ``MAX_LINES``."""
        rows = min(max(self.wrapped_document.height, 1), self.MAX_LINES)
        new_height = rows + self.styles.gutter.height
        if self.styles.height is None or self.styles.height.value != new_height:
            self.styles.height = new_height
        self.call_after_refresh(self.scroll_cursor_visible)


__all__ = ["CYAN", "DIM", "GREEN", "MAGENTA", "RED", "YELLOW", "ActivityBar", "DetailPanel", "HangingText", "KeyHints", "PromptBox", "TranscriptLog", "WorkPanel", "hanging"]
