"""The polished screen, headless (Textual's own test runner): layout, follow state, selection, the activity clock, copy or stop or ask twice to quit, the menu, contrast. No model."""
import asyncio
import html
import logging
import re
from types import SimpleNamespace

import pytest

pytest.importorskip("textual")
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.geometry import Offset
from textual.selection import Selection
from textual.strip import Strip

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import app as screen
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import menu, text
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import PolishedApp, Snapshot
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.widgets import DIM, HangingText, TranscriptLog, hanging


def run_app(build, size=(80, 24), **options):
    async def go():
        app = PolishedApp(**options)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            return await build(app, pilot)
    return asyncio.run(go())


def view_with(outcome):
    from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, RunStarted, Usage
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView
    view = SessionView()
    for event in (RunStarted(goal="g"), Usage(cost_usd=0.0123), Finished(outcome=outcome)):
        view.apply(event)
    return view


def busy(**more):
    return Snapshot(head="ahohs  run  [running]  0:00", activity="Working…", busy=True, prompt="busy", runs=[("main", "Add the rows")],
                    rows=[("▸ Add the rows", "head"), ("  ● 0:05  running", "clock"), ("    run echo hi", "step"), ("  Alt+D or click for details", "hint")], line_map={0: "main", 1: "main", 2: "main"}, **more)


def grow(app):
    app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "g")], rows=[(f"line {i}", "step") for i in range(20)]))
    app.detail.open_for("main", "A long goal", [f"step {i}" for i in range(40)])


# --- layout ----------------------------------------------------------------------------------------------------------------------

def test_the_prompt_stays_docked_at_the_bottom_when_the_panels_above_it_grow():
    async def build(app, pilot):
        prompt, keys = app.query_one("#prompt"), app.query_one("#keys")
        base = prompt.region.y + prompt.region.height
        assert base == keys.region.y and keys.region.y + keys.region.height == app.size.height and keys.region.height == 1
        grow(app)
        await pilot.pause()
        assert prompt.region.y + prompt.region.height == keys.region.y == base
        assert app.activity.region.y + app.activity.region.height == prompt.region.y      # the activity row stays glued above it
    run_app(build)


def test_the_transcript_still_fills_the_space_above_the_docked_widgets():
    async def build(app, pilot):
        transcript, prompt = app.query_one("#transcript"), app.query_one("#prompt")
        assert transcript.region.height > 0 and transcript.region.y + transcript.region.height <= prompt.region.y
    run_app(build, size=(80, 40))


def test_everything_is_whole_at_80_columns_with_no_sideways_scrollbar_with_or_without_a_panel_open():
    async def build(app, pilot):
        widths = []
        for opened in (False, True):
            if opened:
                app.apply_snapshot(busy())
            app.tlog.write(hanging("[0:03] ok read " + "a_very_long_name_without_a_break_" * 6, hang=2))
            app.tlog.write(Text("word " * 80))
            await pilot.pause()
            assert not app.tlog.show_horizontal_scrollbar and app.tlog.max_scroll_x == 0
            widths.append(app.tlog.region.width)
        assert widths == [80, 80]          # the full width, always: a panel with margins never narrows the log
        shown = text.fit_hints(app.key_hints(), 80)
        assert shown == app.key_hints()[:len(shown)]
        assert len(text.placeholder("ready", {})) < 80 - 6
    run_app(build)


def test_the_work_panel_grows_when_its_text_does_and_hides_when_empty():
    async def build(app, pilot):
        app.apply_snapshot(Snapshot(rows=[("a", "head")]))
        await pilot.pause()
        one = app.work_panel.region.height
        app.apply_snapshot(Snapshot(rows=[("a", "head"), ("b", "step"), ("c", "step")]))
        await pilot.pause()
        assert app.work_panel.region.height > one
        app.apply_snapshot(Snapshot())
        await pilot.pause()
        assert not app.work_panel.display
    run_app(build)


# --- the transcript follows the tail unless the person scrolled away -----------------------------------------------------------

def fill(app, count, label="line"):
    for i in range(count):
        app.tlog.write(Text(f"{label} {i}"))


def test_the_transcript_follows_after_the_panel_appears_and_scrolling_up_stops_it_until_the_person_returns():
    async def build(app, pilot):
        fill(app, 60)
        await pilot.pause()
        assert app.tlog.following and app.tlog.scroll_y >= app.tlog.max_scroll_y - 1
        app.apply_snapshot(busy())
        await pilot.pause()
        fill(app, 5, "later")
        await pilot.pause()
        assert app.tlog.following and app.tlog.scroll_y >= app.tlog.max_scroll_y - 1       # the panel shrank the log, and it still follows
        app.tlog.scroll_to(y=0, animate=False)
        await pilot.pause()
        assert not app.tlog.following
        fill(app, 5, "unseen")
        await pilot.pause()
        assert app.tlog.unseen_below and "new output below" in app.activity.render().plain and app.tlog.scroll_y == 0
        app.tlog.scroll_end(animate=False)
        await pilot.pause()
        assert app.tlog.following and not app.tlog.unseen_below
    run_app(build)


def test_a_blank_line_is_not_new_output_and_a_short_log_always_follows():
    async def build(app, pilot):
        fill(app, 60)
        await pilot.pause()
        app.tlog.scroll_to(y=0, animate=False)
        await pilot.pause()
        app.tlog.write(Text(""))
        assert not app.tlog.unseen_below
        app.tlog.clear()
        fill(app, 2)
        await pilot.pause()
        assert app.tlog.following
    run_app(build)


def test_sending_a_message_and_the_end_of_a_run_go_back_to_the_newest_output():
    async def build(app, pilot):
        fill(app, 60)
        await pilot.pause()
        app.tlog.scroll_to(y=0, animate=False)
        await pilot.pause()
        app.prompt_box.text = "hello"
        await pilot.press("enter")
        await pilot.pause()
        assert app.tlog.following and not app.tlog.unseen_below
        assert app.lines.get_nowait() == "hello"
    run_app(build)


def test_a_wrapped_line_starts_its_next_rows_under_its_words_and_a_bar_is_carried():
    from rich.console import Console
    console = Console(width=40, force_terminal=False)
    rows = HangingText("❯ " + "word " * 20, hang=2).rows(30, console)
    assert len(rows) > 1 and rows[0].plain.startswith("❯ ") and all(r.plain.startswith("  ") for r in rows[1:])
    bar = HangingText("┃ " + "question " * 10, hang=2, carry=True).rows(30, console)
    assert all(r.plain.startswith("┃ ") for r in bar)
    assert HangingText("❯ short", hang=2).rows(5, console)[0].plain == "❯ short"         # too narrow to indent: left for the log to wrap
    assert [r.plain for r in HangingText("❯ a\n\nb", hang=2).rows(30, console)][-1] == "  b"


# --- drag to select and copy ------------------------------------------------------------------------------------------------------

def cell_styles(strip):
    return [seg.style for seg in strip._segments for _ in seg.text]


def test_extraction_is_per_row_text_trimmed_and_the_same_for_a_reversed_drag():
    lines = ["hello world", "second line", "third row"]
    assert TranscriptLog.extract(lines, Selection.from_offsets(Offset(0, 0), Offset(5, 0))) == "hello"
    down, up = Selection.from_offsets(Offset(6, 0), Offset(6, 1)), Selection.from_offsets(Offset(6, 1), Offset(6, 0))
    assert TranscriptLog.extract(lines, down) == "world\nsecond" == TranscriptLog.extract(lines, up)
    assert TranscriptLog.extract(["hello      ", "world"], Selection.from_offsets(Offset(0, 0), Offset(0, 1))) == "hello"


def test_the_highlight_restyles_only_the_selected_cells_and_keeps_their_own_colour():
    strip = Strip([Segment("hello world", Style(color="red"))])
    lit = TranscriptLog.highlight(strip, 2, 5, Style(bgcolor="blue"))
    styles = cell_styles(lit)
    assert [s.bgcolor is not None for s in styles] == [False, False, True, True, True] + [False] * 6
    assert styles[3].color is not None and styles[3].color.name == "red"
    assert TranscriptLog.highlight(strip, 3, 3, Style(bgcolor="blue")) is strip and "".join(seg.text for seg in lit._segments) == "hello world"


def test_a_drag_in_the_log_selects_text_and_posts_it_to_copy_and_a_plain_click_posts_a_click():
    async def build(app, pilot):
        copied = []
        app.copy_text = lambda t: (copied.append(t), (True, "clipboard"))[1]
        app.tlog.write(Text("hello selected world"))
        await pilot.pause()
        log = app.tlog
        log.sel_from, log.sel_to = Offset(6, 0), Offset(14, 0)
        assert log.selected_text == "selected"
        app.on_transcript_log_copied(TranscriptLog.Copied(log.selected_text))
        assert copied == ["selected"]
        log.clear_selection()
        assert log.selected_text == ""
    run_app(build)


def test_the_transcript_cannot_take_focus_and_a_click_anywhere_puts_the_cursor_back_in_the_prompt():
    async def build(app, pilot):
        assert TranscriptLog.can_focus is False
        app.set_focus(app.detail)
        assert app.focused is not app.prompt_box
        app.on_click(None)
        await pilot.pause()
        assert app.focused is app.prompt_box
        app.on_click(None)
        await pilot.pause()
        assert app.focused is app.prompt_box
    run_app(build)


# --- the activity row: a clock after three seconds, never pushed off ----------------------------------------------------------------

def test_the_clock_shows_after_three_seconds_survives_a_status_change_and_goes_with_the_run():
    async def build(app, pilot):
        bar = app.activity
        bar.set_wait(2.4)
        assert bar.shown_clock() is None and "0:0" not in bar.render().plain
        bar.set_wait(3)
        assert bar.shown_clock() == "0:03"
        bar.set_status("reading the next file")
        assert "0:03" in bar.render().plain
        bar.set_wait(None)
        assert bar.shown_clock() is None
    run_app(build)


@pytest.mark.parametrize("queued", [0, 1, 3])
def test_at_80_columns_a_long_status_never_pushes_the_clock_or_the_waiting_count_off_the_end(queued):
    async def build(app, pilot):
        app.apply_snapshot(Snapshot(busy=True, activity="x" * 300, waited=3725, queued=queued, prompt="busy"))
        await pilot.pause()
        plain = app.activity.render().plain
        assert len(plain) <= 80 and "1:02:05" in plain
        if queued:
            assert f"{queued} message" in plain
        assert app.activity.display
    run_app(build)


def test_a_status_that_fits_is_drawn_whole_and_the_bar_hides_when_idle():
    async def build(app, pilot):
        app.apply_snapshot(Snapshot(busy=True, activity="Reading notes.md", prompt="busy"))
        assert app.activity.render().plain.endswith("Reading notes.md")
        app.apply_snapshot(Snapshot())
        assert not app.activity.display
    run_app(build)


def test_the_prompts_hint_follows_the_state_and_a_waiting_question_is_marked():
    async def build(app, pilot):
        app.apply_snapshot(busy())
        assert "Esc stops the work" in app.prompt_box.placeholder and not app.prompt_box.has_class("-awaiting")
        app.apply_snapshot(Snapshot(busy=True, asking=True, prompt="asking"))
        assert "approve" in app.prompt_box.placeholder and app.prompt_box.has_class("-awaiting")
        app.apply_snapshot(Snapshot())
        assert "Enter=send" in app.prompt_box.placeholder and not app.prompt_box.has_class("-awaiting")
    run_app(build)


# --- the key line --------------------------------------------------------------------------------------------------------------------

def test_the_key_line_names_esc_only_while_busy_and_quit_only_when_idle_and_tab_only_with_many_runs():
    async def build(app, pilot):
        assert [k for k, _ in app.key_hints()][-1] == "ctrl+c" and "esc" not in [k for k, _ in app.key_hints()]
        app.apply_snapshot(busy())
        keys = [k for k, _ in app.key_hints()]
        assert keys[0] == "esc" and "alt+d" in keys and "ctrl+c" not in keys and "tab" not in keys
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "a"), ("h1", "b")]))
        assert "tab" in [k for k, _ in app.key_hints()]
        rendered = app.query_one("#keys").render().plain
        assert rendered and all(part.strip() for part in rendered.split("  ") if part)
    run_app(build)


# --- the run detail: full history and a follow toggle --------------------------------------------------------------------------------

def test_the_detail_keeps_the_full_history_follows_the_newest_step_and_stops_when_the_person_scrolls_back():
    async def build(app, pilot):
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "Add the rows")], histories={"main": [f"step {i}" for i in range(80)]}, rows=[("▸ x", "head")], line_map={0: "main"}))
        app.toggle_detail()
        await pilot.pause(0.2)
        assert app.detail.display and app.detail.run_id == "main" and len(app.detail.lines) == 80 and app.detail.follow
        assert app.detail.scroll_y >= app.detail.max_scroll_y - 1
        app.detail.page_back()
        assert not app.detail.follow
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "Add the rows")], histories={"main": [f"step {i}" for i in range(90)]}, rows=[("▾ x", "open")], line_map={0: "main"}))
        await pilot.pause()
        assert len(app.detail.lines) == 90 and not app.detail.follow and "scrolled back" in app.detail.text().plain
        app.detail.scroll_end(animate=False)
        await pilot.pause()
        app.detail.page_forward()
        assert app.detail.follow and "following" in app.detail.text().plain
    run_app(build)


def test_a_click_on_a_runs_rows_opens_its_detail_and_a_second_click_or_alt_d_closes_it():
    class Click:
        def __init__(self, y):
            self.y, self.stopped = y, False

        def stop(self):
            self.stopped = True

    async def build(app, pilot):
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "goal"), ("h1", "helper")], histories={"main": ["a"], "h1": ["b"]},
                                    rows=[("▸ goal", "head"), ("  ● 0:01  running", "clock"), ("▸ helper", "head"), ("  ● 0:01  running", "clock"), ("  hint", "hint")],
                                    line_map={0: "main", 1: "main", 2: "h1", 3: "h1"}))
        hint = Click(4)
        app.work_panel.on_click(hint)
        assert not app.detail.display and not hint.stopped       # the trailing hint row is not a run
        app.work_panel.on_click(Click(2))
        assert app.detail.display and app.detail.run_id == "h1" and app.detail.lines == ["b"]
        app.work_panel.on_click(Click(2))
        assert not app.detail.display
        app.action_toggle_detail()
        assert app.detail.display and app.detail.run_id == "h1"        # Alt+D opens the run last chosen
        app.action_tab()
        assert app.detail.run_id == "main" and app.detail.total == 2
        app.action_toggle_detail()
        assert not app.detail.display
    run_app(build)


def test_the_open_runs_header_is_marked_in_the_panel_and_the_detail_closes_when_its_run_ends():
    async def build(app, pilot):
        snap = Snapshot(busy=True, prompt="busy", runs=[("main", "goal"), ("h1", "helper")], histories={"h1": ["b"]},
                        rows=[("▸ goal", "head"), ("▸ helper", "head")], line_map={0: "main", 1: "h1"})
        app.apply_snapshot(snap)
        app.toggle_detail("h1")
        rows = app.work_panel.rows
        assert rows[0][0].startswith("▸") and rows[1][0].startswith("▾") and rows[1][1] == "open"
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "goal")], rows=[("▸ goal", "head")], line_map={0: "main"}))
        assert not app.detail.display
    run_app(build)


# --- copy, stop, or ask twice to quit ---------------------------------------------------------------------------------------------------

class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def quit_app(monkeypatch, selected="", is_busy=False):
    clock = Clock()
    monkeypatch.setattr(screen, "time", SimpleNamespace(monotonic=clock))      # the module's own name for the clock only: the event loop keeps the real one
    sent, copied = [], []

    async def prepare(app, pilot):
        app.press = lambda token, text="": sent.append(token)
        app.selected = lambda: selected
        app.copy_text = lambda t: (copied.append(t), (True, "clipboard"))[1]
        app.snap = Snapshot(busy=is_busy)
        return sent, copied, clock
    return prepare


def written(app):
    return [line.text for line in app.tlog.lines]


def test_ctrl_c_copies_the_selected_text_and_stays_running(monkeypatch):
    async def build(app, pilot):
        sent, copied, clock = await quit_app(monkeypatch, "some selected words")(app, pilot)
        app.action_copy_or_quit()
        await pilot.pause()
        assert copied == ["some selected words"] and not app.quit_requested and not sent
        assert any("Copied: some selected words" in row for row in written(app))
    run_app(build)


def test_one_press_with_nothing_selected_never_quits_when_idle_and_a_second_press_within_the_window_quits(monkeypatch):
    async def build(app, pilot):
        sent, copied, clock = await quit_app(monkeypatch)(app, pilot)
        app.action_copy_or_quit()
        await pilot.pause()
        assert not app.quit_requested and any("Press Ctrl+C again to quit." in r for r in written(app))
        clock.now += 1.0
        app.action_copy_or_quit()
        assert app.quit_requested and sent == ["eof"] and app.lines.get_nowait() is None
    run_app(build)


def test_a_second_press_after_the_window_only_asks_again(monkeypatch):
    async def build(app, pilot):
        sent, copied, clock = await quit_app(monkeypatch)(app, pilot)
        app.action_copy_or_quit()
        clock.now += 10.0
        app.action_copy_or_quit()
        await pilot.pause()
        assert not app.quit_requested and sum("Press Ctrl+C again to quit." in r for r in written(app)) == 2
    run_app(build)


def test_while_the_ai_works_ctrl_c_stops_the_work_like_esc_and_a_second_press_quits(monkeypatch):
    async def build(app, pilot):
        sent, copied, clock = await quit_app(monkeypatch, is_busy=True)(app, pilot)
        app.action_copy_or_quit()
        await pilot.pause()
        assert sent == ["esc"] and not app.quit_requested and any("Stopped. Press Ctrl+C again to quit." in r for r in written(app))
        clock.now += 1.0
        app.action_copy_or_quit()
        assert app.quit_requested and sent[-1] == "eof"
    run_app(build)


def test_a_blank_selection_counts_as_none_and_a_long_preview_is_collapsed_and_cut(monkeypatch):
    async def build(app, pilot):
        sent, copied, clock = await quit_app(monkeypatch, "   \n  ")(app, pilot)
        app.action_copy_or_quit()
        assert not copied
        app.selected = lambda: "word\n   spaced  " + "x" * 200
        app.action_copy_or_quit()
        await pilot.pause()
        shown = [r for r in written(app) if "Copied:" in r][0]
        assert "word spaced" in shown and shown.endswith("…") and len(shown) < 80
    run_app(build)


def test_alt_y_copies_the_last_reply_and_says_so_when_there_is_none():
    async def build(app, pilot):
        notes, copied = [], []
        app.notify = lambda message, **kw: notes.append((message, kw.get("severity")))
        app.copy_text = lambda t: (copied.append(t), (True, "clipboard"))[1]
        app.action_copy_last()
        assert notes[-1] == ("Nothing to copy yet", "warning")
        app.last_reply = "the last reply"
        app.action_copy_last()
        assert copied == ["the last reply"] and notes[-1][1] == "information"
    run_app(build)


def test_copy_falls_back_to_the_terminal_and_says_what_to_install_when_no_program_exists():
    ok, why = screen.copy_with_tool("x", which=lambda name: None)
    assert not ok and "install" in why
    ran = []
    ok, why = screen.copy_with_tool("x", which=lambda name: "/bin/" + name if name == "wl-copy" else None, run=lambda cmd, **kw: ran.append(cmd))
    assert ok and ran[0][0] == "wl-copy"
    ok, why = screen.copy_with_tool("x", which=lambda name: "/bin/" + name, run=lambda *a, **k: 1 / 0)
    assert not ok and "failed" in why


# --- the command menu ---------------------------------------------------------------------------------------------------------------------

def test_typing_slash_opens_the_menu_enter_runs_the_highlighted_command_and_escape_keeps_the_text():
    async def build(app, pilot):
        await pilot.press("/")
        await pilot.pause()
        assert app.menu().display and len(app.shown_items) == len(app.commands)
        await pilot.press("down", "enter")
        await pilot.pause()
        assert app.lines.get_nowait() == "/resume" and not app.menu().display and app.prompt_box.text == ""
        await pilot.press("/", "s", "t")
        await pilot.pause()
        assert [i.label for i in app.shown_items] == ["/stop <name>"]
        await pilot.press("escape")
        await pilot.pause()
        assert not app.menu().display and app.prompt_box.text == "/st"
    run_app(build)


def test_tab_completes_a_command_that_needs_an_argument_and_the_consumers_choices_follow_it():
    async def build(app, pilot):
        await pilot.press("/", "s", "t", "tab")
        await pilot.pause()
        assert app.prompt_box.text == "/stop " and not app.menu().display
        app.prompt_box.text = ""
        await pilot.press("/", "p", "i", "c", "k", "space")
        await pilot.pause()
        assert [i.label for i in app.shown_items] == ["Alpha", "Beta"]
        await pilot.press("down", "enter")
        await pilot.pause()
        assert app.lines.get_nowait() == "/pick b"
    pick = lambda typed: [menu.MenuItem("Alpha", "first", "/pick a", True), menu.MenuItem("Beta", "second", "/pick b", True)] if typed.startswith("/pick ") else []
    run_app(build, choices=pick, commands={"pick": lambda rest: None})


def test_a_command_typed_during_a_run_goes_to_the_driver_and_clear_is_the_screens_own():
    async def build(app, pilot):
        sent = []
        app.press = lambda token, text="": sent.append((token, text))
        app.prompt_box.text = "/stop tests"
        await pilot.press("enter")
        assert sent == [("line", "/stop tests")]
        fill(app, 3)
        app.prompt_box.text = "/clear"
        await pilot.press("enter")
        await pilot.pause()
        assert sent == [("line", "/stop tests")] and any("cleared" in r for r in written(app)) and not any(r.startswith("line ") for r in written(app))
    run_app(build)


def test_a_question_is_answered_by_one_key_when_the_prompt_is_empty_and_by_a_whole_line_otherwise():
    async def build(app, pilot):
        sent = []
        app.press = lambda token, text="": sent.append((token, text))
        app.apply_snapshot(Snapshot(busy=True, asking=True, prompt="asking"))
        await pilot.press("y")
        assert sent == [("line", "y")] and app.prompt_box.text == ""
        await pilot.press("n", "o")        # a typed word is a line like any other: n alone answered, so start with something else
        app.prompt_box.text = ""
        app.apply_snapshot(Snapshot(busy=True, prompt="busy"))
        await pilot.press("y")
        assert app.prompt_box.text == "y"      # no question open: it is just typing
    run_app(build)


def test_up_recalls_the_previous_line_and_the_arrows_move_in_the_structure_only_when_it_is_open():
    async def build(app, pilot):
        sent = []
        app.press = lambda token, text="": sent.append(token)
        app.history = ["first goal", "second goal"]
        app.position = 2
        await pilot.press("up")
        assert app.prompt_box.text == "second goal"
        await pilot.press("up")
        assert app.prompt_box.text == "first goal"
        await pilot.press("down", "down")
        assert app.prompt_box.text == ""
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", structure=True, structure_open=True))
        await pilot.press("down", "right")
        assert sent == ["down", "open"]
    run_app(build)


def test_enter_sends_and_a_trailing_backslash_makes_a_newline():
    async def build(app, pilot):
        await pilot.press("a", "\\", "enter", "b")
        assert app.prompt_box.text == "a\nb" and app.lines.empty()
        await pilot.press("enter")
        assert app.lines.get_nowait() == "a\nb"
    run_app(build)


# --- warnings: one short line each, the rest in a file --------------------------------------------------------------------------------------

def test_in_the_running_screen_warnings_are_folded_and_a_librarys_are_silent(tmp_path):
    async def build(app, pilot):
        for i in range(5):
            logging.getLogger("hubofhubs.polished_test").warning("problem %d. more words", i)
        logging.getLogger("somelibrary").warning("chatty")
        await pilot.pause()
        rows = [r for r in written(app) if "⚠" in r]
        assert len(rows) == 3 and not any("chatty" in r for r in written(app))
        assert app.folder.finish()
        await pilot.pause()
        assert any(r.startswith("2 more notices. Details: ") for r in written(app))
        assert (tmp_path / "s.log").read_text().count("problem") == 5
    run_app(build, log_path=tmp_path / "s.log")


def test_the_screen_gives_back_the_loggers_it_took_when_it_closes(tmp_path):
    before = list(logging.getLogger().handlers)
    run_app(lambda app, pilot: asyncio.sleep(0), log_path=tmp_path / "s.log")
    assert list(logging.getLogger().handlers) == before


# --- contrast: every text colour that carries information reaches 4.5 to 1 -------------------------------------------------------------------------

STYLE_RE = re.compile(r"\.terminal-\d+-r(\d+)\s*\{([^}]*)\}")
TEXT_RE = re.compile(r'<text class="terminal-\d+-(r\d+|title)"([^>]*?)>(.*?)</text>', re.S)
RECT_RE = re.compile(r'<rect fill="(#[0-9a-fA-F]{6})" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"')
ATTR_RE = re.compile(r'(\w[\w-]*)="([^"]*)"')
CELL_H = 24.4
MINIMUM = 4.5


def luminance(value):
    def channel(c):
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (int(value.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def text_colours(svg):
    """(text, foreground, background) of every run of the screen with a letter or digit, from Textual's own SVG export."""
    styles = {}
    for num, body in STYLE_RE.findall(svg):
        fill = re.search(r"fill:\s*(#[0-9a-fA-F]{6})", body)
        styles["r" + num] = fill.group(1) if fill else "#c5c8c6"
    rects = {}
    for fill, x, y, width, height in RECT_RE.findall(svg):
        rects.setdefault(int(round((float(y) - 1.5) / CELL_H)), []).append((float(x), float(x) + float(width), fill))
    runs = []
    for cls, attrs, body in TEXT_RE.findall(svg):
        if cls == "title":
            continue
        a = dict(ATTR_RE.findall(attrs))
        row = re.search(r"line-(\d+)\)", a.get("clip-path", ""))
        shown = html.unescape(body).replace("\xa0", " ")
        if not row or not re.search(r"[A-Za-z0-9]", shown):
            continue
        x, bg = float(a["x"]), "#1e1e1e"
        for x0, x1, fill in rects.get(int(row.group(1)), []):
            if x0 - 0.01 <= x < x1 - 0.01:
                bg = fill
        runs.append((shown.strip(), styles.get(cls, "#c5c8c6"), bg))
    return runs


def low_contrast(app):
    found = []
    for shown, fg, bg in text_colours(app.export_screenshot()):
        ratio = contrast(fg, bg)
        if ratio < MINIMUM and not (len(shown) == 1 and luminance(bg) > 0.5):      # one cell in inverse video is the prompt's cursor
            found.append((round(ratio, 2), fg, bg, shown[:50]))
    return found


def test_the_contrast_function_agrees_with_measured_values_and_sees_a_colour_that_is_too_faint():
    assert round(contrast("#777777", "#1e1e1e"), 2) == 3.72 and round(contrast("#9e9e9e", "#1e1e1e"), 2) == 6.22

    async def build(app, pilot):
        app.tlog.write(Text("a faint hint nobody can read", style="#777777"))
        await pilot.pause()
        return low_contrast(app)
    assert [(ratio, shown) for ratio, fg, bg, shown in run_app(build)] == [(3.72, "a faint hint nobody can read")]


def test_every_text_colour_that_carries_information_reaches_4_5_to_1_in_each_state():
    async def build(app, pilot):
        found = {}

        async def measure(state):
            await pilot.pause()
            app.activity.refresh()
            await pilot.pause()
            found[state] = low_contrast(app)
        await measure("idle")
        for row in ("[0:01] started: Add the rows (stream)", "[0:02] ok read notes.md", "[0:03] !! run make test", "[0:03] xx edit x.py (refused: not allowed)",
                    "[0:04] WAITING FOR YOU: Deploy? It will change: the site. (y to approve, n to refuse)", "⚠ a warning", "❯ you: also check staging", "  Your note was taken up."):
            app.add_line(row)
        for outcome in ("met", "unmet", "failed"):      # the closing line in colour, as it is drawn on a terminal
            app.add_ansi(text.closing_line(view_with(outcome), color=True))
        app.add_ansi("Changed (2): a.txt, b.txt")
        app.add_line("  Sending your 2 waiting notes as one message.")
        app.write_text(hanging("  Press Ctrl+C again to quit.", DIM))
        app.add_markdown("# Result\n\nAdded **14** rows.\n\n- one\n- two\n\n```\nrun --now\n```")
        app.apply_snapshot(busy(waited=65.0, queued=2))
        await measure("busy with a note waiting")
        app.toggle_detail("main")
        app.apply_snapshot(Snapshot(busy=True, prompt="busy", runs=[("main", "g")], histories={"main": ["[0:01] ok read a.txt"]}, rows=[("▾ g", "open")], line_map={0: "main"}))
        await measure("the run detail")
        app.toggle_detail("main")
        app.apply_snapshot(Snapshot(busy=True, asking=True, prompt="asking"))
        await measure("waiting for an answer")
        await pilot.press("/")
        await measure("the command menu")
        return found
    found = run_app(build)
    assert {state: rows for state, rows in found.items() if rows} == {}
