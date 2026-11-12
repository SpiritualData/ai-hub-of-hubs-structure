"""The polished screen's rules as plain functions of a session view: keys, placeholders, the work panel, the closing line, notes, menu, warnings, words. No screen library, no model."""
import logging
import re

import pytest

from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Finished, RunStarted, Step, Usage, Waiting)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import strings
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import menu, notices, text
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import WORDS, say
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView, event_line


def view_of(*events, now=0.0):
    view = SessionView()
    view.now = view.started + now
    for event in events:
        view.apply(event)
    return view


# --- the key line: whole hints only, Esc only while the AI works --------------------------------------------------------------------

def hints(**kw):
    base = dict(busy=False, asking=False, stopped=False, runs=0, detail=False, structure=False)
    return [key for key, _ in text.key_hints(**{**base, **kw})]


def test_esc_is_listed_only_while_the_ai_works_and_ctrl_c_only_when_idle():
    assert hints(busy=True)[0] == "esc" and "ctrl+c" not in hints(busy=True)
    assert "esc" not in hints() and hints()[-1] == "ctrl+c"


def test_a_key_that_would_do_nothing_is_not_listed():
    assert "alt+d" not in hints() and "alt+d" in hints(runs=1)
    assert "tab" not in hints(runs=1) and "tab" in hints(runs=2)
    assert "alt+k" not in hints() and "alt+k" in hints(stopped=True)
    assert "alt+t" not in hints() and "alt+t" in hints(structure=True)
    assert hints(busy=True, asking=True)[0] == "y/n"


@pytest.mark.parametrize("room", [10, 20, 33, 47, 60, 79, 80, 120])
def test_the_key_line_shows_whole_hints_and_never_a_key_cut_in_half(room):
    every = text.key_hints(busy=True, asking=True, stopped=False, runs=3, detail=True, structure=True)
    shown = text.fit_hints(every, room)
    assert shown == every[:len(shown)]
    assert sum(len(k) + 1 + len(label) for k, label in shown) + 2 * max(len(shown) - 1, 0) <= room


def test_the_busy_placeholder_names_the_key_that_stops_the_work_and_the_ready_one_fits_at_80_columns():
    assert "Esc stops the work" in text.placeholder("busy")
    assert len(text.placeholder("ready", {})) <= 76 and len(text.placeholder("ready", {"VTE_VERSION": "1"})) <= 76
    assert "Ctrl+J or Alt+Enter" in text.placeholder("ready", {"VTE_VERSION": "1"})
    assert "y" in text.placeholder("asking") and "resume" in text.placeholder("stopped")


# --- one clock and one elapsed format ----------------------------------------------------------------------------------------------

def test_one_clock_format_everywhere_and_a_clock_only_after_three_seconds():
    assert [text.clock(s) for s in (0, 5, 65, 3725)] == ["0:00", "0:05", "1:05", "1:02:05"]
    view = view_of(RunStarted(goal="g"), Usage(cost_usd=0.01), now=125)
    assert "2:05" in text.header_text(view)
    assert "2:05" in text.closing_line(view)
    rows, _ = text.dashboard(view)
    assert any("2:05" in row for row, _ in rows)
    assert text.CLOCK_AFTER == 3
    for row in [text.header_text(view), text.closing_line(view)] + [r for r, _ in rows]:
        assert not re.search(r"\d+m\d+s|\b\d+s\b", row), row


# --- the work panel: calm, a few rows a run, one home for each update -----------------------------------------------------------------

def running(view_steps, helpers=0):
    events = [RunStarted(goal="Add the rows")]
    events += [AgentStarted(agent_id=f"h{i}", task=f"helper {i}") for i in range(helpers)]
    events += view_steps
    return view_of(*events, now=9)


def test_the_panel_shows_three_output_rows_for_one_run_and_tightens_with_more_runs():
    steps = [Step(step_id=f"s{i}", kind="run", label=f"cmd {i}", state="running") for i in range(6)]
    one = running(steps)
    rows, _ = text.dashboard(one)
    assert [kind for _, kind in rows].count("step") == 3
    assert [text.lines_per_run(n) for n in (1, 2, 3, 6)] == [3, 2, 1, 1]
    many = running([Step(step_id=f"{a}{i}", kind="run", label=f"cmd {i}", state="running", agent_id=a) for i in range(4) for a in ("main", "h0", "h1")], helpers=2)
    rows, _ = text.dashboard(many)
    assert [kind for _, kind in rows].count("step") == 3        # one row for each of three runs


def test_a_click_row_belongs_to_the_run_it_fell_in_and_the_hint_row_to_none():
    view = running([Step(step_id="a", kind="read", label="a/b.txt", state="running"), Step(step_id="b", kind="run", label="x", state="running", agent_id="h0")], helpers=1)
    rows, line_map = text.dashboard(view, active="h0")
    heads = [i for i, (row, kind) in enumerate(rows) if kind in ("head", "open")]
    assert line_map[heads[0]] == "main" and line_map[heads[1]] == "h0"
    assert rows[heads[1]][0].startswith("▾") and rows[heads[0]][0].startswith("▸")
    assert len(rows) - 1 not in line_map and rows[-1][1] == "hint"
    assert any(row.startswith("  → ") for row, _ in rows)        # a path-like target gets the arrow


def test_nothing_is_drawn_when_nothing_runs():
    assert text.dashboard(view_of(RunStarted(goal="g"), Finished(outcome="met"))) == ([], {})


def test_the_transcript_keeps_what_finished_and_the_panel_what_is_happening_now():
    running_step = Step(step_id="s1", kind="edit", label="b.txt", state="running")
    view = view_of(RunStarted(goal="g"), running_step)
    assert event_line(running_step, view, True) == ""
    assert any("b.txt" in row for row, _ in text.dashboard(view)[0])
    done = Step(step_id="s1", kind="edit", label="b.txt", state="done")
    view.apply(done)
    assert "ok edit" in event_line(done, view, True)
    assert not any("b.txt" in row for row, _ in text.dashboard(view)[0])
    started = AgentStarted(agent_id="h", task="tests")
    assert event_line(started, view, True) == "" and event_line(Usage(cost_usd=1.0), view, True) == ""


def test_the_detail_holds_a_runs_full_history_in_order_newest_last():
    steps = [Step(step_id=f"s{i}", kind="read", label=f"f{i}.txt", state="done", at=i) for i in range(30)]
    view = running(steps)
    lines = text.history_lines(view, "main")
    assert len(lines) == 30 and "f0.txt" in lines[0] and "f29.txt" in lines[-1] and lines[1].startswith("[0:01]")


# --- the closing: structured fields only, one shape ------------------------------------------------------------------------------------

@pytest.mark.parametrize("outcome,words", [("met", "Done: the goal was met"), ("unmet", "Finished: the goal was not met"), ("stopped", "Stopped: your work is kept"), ("failed", "Failed")])
def test_the_closing_line_is_the_outcomes_words_the_time_and_the_cost(outcome, words):
    view = view_of(RunStarted(goal="g"), Usage(cost_usd=0.0123, calls=3), Finished(outcome=outcome), now=42)
    line = text.closing_line(view)
    assert line.startswith(words) and "0:42" in line and "$0.0123" in line and "3 calls" in line


def test_the_words_of_the_report_never_decide_the_outcome():
    view = view_of(RunStarted(goal="g"), Finished(outcome="failed", report="Done! Everything worked perfectly. The goal was met."))
    assert text.closing_line(view).startswith("Failed") and "Done" not in text.closing_line(view)
    again = view_of(RunStarted(goal="g"), Finished(outcome="met", report="Failed to do anything."))
    assert text.closing_line(again).startswith("Done: the goal was met")


def test_a_cost_nobody_reported_is_unknown_never_zero_and_a_ceiling_is_shown_against_it():
    view = view_of(RunStarted(goal="g"), Finished(outcome="met"))
    assert "cost unknown" in text.closing_line(view) and "$0" not in text.closing_line(view)
    capped = view_of(RunStarted(goal="g"), Usage(cost_usd=1.5, ceiling_usd=5.0), Finished(outcome="met"))
    assert "$1.50 of $5.00" in text.closing_line(capped)


def test_the_metric_before_and_after_is_once_first_and_the_closing_line_last():
    view = view_of(RunStarted(goal="g", metric="checks", metric_before=1.0, solution="s", milestone="m"), Step(step_id="e", kind="edit", label="a.txt"),
                   Finished(outcome="met", metric_after=3.0, changed=("a.txt",)), now=5)
    above, closing = text.closing_rows(view)
    assert above[0] == "Metric checks: before 1, after 3 (+2)" and sum("before 1" in r for r in above + closing) == 1
    assert any(r.startswith("Changed (1): a.txt") for r in above) and any(r.startswith("Served: s") for r in above)
    assert len(closing) == 1 and closing[0].startswith("Done: the goal was met")
    assert not any(r.startswith("Cost and time") for r in above)      # the closing line carries it: each fact has one home


def test_a_color_closing_marks_the_outcome_and_a_plain_one_has_no_escape_codes():
    view = view_of(RunStarted(goal="g"), Finished(outcome="met"))
    assert "\x1b[" not in text.closing_line(view) and "\x1b[38;5;77m" in text.closing_line(view, color=True)


# --- notes typed while the AI works ----------------------------------------------------------------------------------------------------

def test_what_counts_as_a_note_and_what_is_a_command_an_answer_or_a_control_word():
    ok = dict(running=True, stopping=False, asking=False)
    assert text.is_note("use the short name", **ok) and text.is_note("y", **ok)
    for word in ("/stop x", "@helper do it", "resume", "quit", "?", ""):
        assert not text.is_note(word, **ok), word
    assert not text.is_note("y", running=True, stopping=False, asking=True)
    assert text.is_note("also tidy up", running=True, stopping=False, asking=True)
    assert not text.is_note("a note", running=False, stopping=False, asking=False)
    assert not text.is_note("a note", running=True, stopping=True, asking=False)


def test_several_notes_combine_into_one_message_in_the_order_typed_and_a_note_is_never_repeated():
    assert text.combine_notes(["first", " second ", "", "third"]) == "first\n\nsecond\n\nthird"
    assert text.leftover_notes(["b"], ["c", "b"], ["a"]) == ["a", "b", "c"]
    assert text.waiting_notes(view_of(RunStarted(goal="g")), held=2) == 2


def test_the_note_lines_say_it_once_in_singular_and_plural():
    assert text.pickup_line(1) == "Your note was taken up." and "3 notes" in text.pickup_line(3)
    assert text.flush_line(1) == "Sending your 1 waiting note as the next message." and "2 waiting notes as one message" in text.flush_line(2)
    assert text.back_in_box_line(1).startswith("Your note is back in the box") and text.back_in_box_line(2).startswith("Your 2 notes are back")


# --- the status is true -----------------------------------------------------------------------------------------------------------------------

def test_the_activity_says_what_is_running_and_the_prompt_state_follows_the_view():
    view = view_of(RunStarted(goal="g"), Step(step_id="r", kind="read", label="notes.md", state="running"))
    assert text.activity_text(view) == "Reading notes.md" and text.prompt_state(view, True) == "busy"
    view.apply(Step(step_id="r", kind="read", label="notes.md", state="done"))
    assert text.activity_text(view) == "Working…"
    view.apply(Waiting(ask_id="a", question="Deploy?"))
    assert text.activity_text(view) == "Waiting for your answer" and text.prompt_state(view, True) == "asking"
    view.status, view.asking = "stopping", None
    assert text.activity_text(view) == "Stopping…"
    view.status = "stopped"
    assert text.prompt_state(view, False) == "stopped" and text.prompt_state(SessionView(), False) == "ready"


def test_runs_are_the_main_run_while_it_lasts_and_each_helper_still_working():
    view = view_of(RunStarted(goal="g"), AgentStarted(agent_id="h1", task="tests", solution="qa"), AgentStarted(agent_id="h2", task="docs"), AgentEnded(agent_id="h2", state="met"))
    assert [(r.agent_id, r.title) for r in text.runs_of(view)] == [("main", "g"), ("h1", "tests (qa)")]
    view.apply(Finished(outcome="met"))
    assert [r.agent_id for r in text.runs_of(view)] == ["h1"]


# --- the command menu -------------------------------------------------------------------------------------------------------------------------

def test_slash_lists_every_command_and_typing_narrows_it_and_a_command_with_an_argument_only_completes():
    commands = menu.builtin_commands()
    assert len(menu.menu_items("/", commands)) == len(commands) and menu.menu_items("hello", commands) == [] and menu.menu_items("/a\nb", commands) == []
    assert [i.label for i in menu.menu_items("/st", commands)] == ["/stop <name>"]
    stop = menu.menu_items("/stop", commands)[0]
    assert (stop.completion, stop.submit) == ("/stop ", False)
    assert menu.menu_items("/quit", commands)[0].submit is True
    assert menu.menu_items("/stop x", commands) == []       # past the name: nothing more to suggest


def test_a_consumers_commands_are_described_by_their_docstrings_and_its_choices_follow_a_command():
    def release(rest):
        """publish the next release"""
    commands = menu.builtin_commands() + menu.custom_commands({"release": release, "plain": lambda rest: None})
    items = {i.label: i for i in menu.menu_items("/", commands)}
    assert items["/release"].description == "publish the next release" and items["/plain"].description == "a command of this build"
    pick = lambda typed: [menu.MenuItem("Alpha", "the first", "/choose a", True), menu.MenuItem("Beta", "the second", "/choose b", True)]
    assert [i.label for i in menu.menu_items("/choose ", commands, pick)] == ["Alpha", "Beta"]
    assert menu.menu_items("/choose ", commands, lambda typed: 1 / 0) == []


# --- warnings folded ----------------------------------------------------------------------------------------------------------------------------

class Lines:
    def __init__(self):
        self.out = []

    def __call__(self, line):
        self.out.append(line)


def record(name, message, level=logging.WARNING, **extra):
    made = logging.LogRecord(name, level, __file__, 1, message, (), None)
    for key, value in extra.items():
        setattr(made, key, value)
    return made


def test_a_warning_is_one_short_line_the_rest_counted_once_and_every_record_is_in_the_file(tmp_path):
    shown, path = Lines(), tmp_path / "s.log"
    folder = notices.NoticeFolder(shown, None, log_path=path)
    for i in range(5):
        folder.handle(record("hubofhubs.x", f"problem {i}. A long second sentence nobody needs."))
    folder.handle(record("hubofhubs.x", "problem 0. again"))
    folder.finish()
    folder.close()
    assert shown.out[:3] == ["⚠ problem 0", "⚠ problem 1", "⚠ problem 2"]
    assert shown.out[3].startswith("2 more notices. Details: ") and len(shown.out) == 4
    assert folder.finish() is False and path.read_text().count("problem") >= 6


def test_an_error_is_always_shown_a_library_is_silent_and_a_flagged_record_goes_to_the_file_only(tmp_path):
    shown = Lines()
    folder = notices.NoticeFolder(shown, None, log_path=tmp_path / "s.log")
    folder.handle(record("somelib", "chatty warning"))
    folder.handle(record("somelib", "a real failure", logging.ERROR))
    folder.handle(record("somelib", "a real failure", logging.ERROR))
    folder.handle(record("hubofhubs.y", "told the person elsewhere", in_transcript=False))
    assert shown.out == ["⚠ a real failure"]
    folder.begin_run()
    assert shown.out[-1].startswith("Details: ")


def test_a_new_run_counts_afresh_and_verbose_keeps_every_record_in_full(tmp_path):
    shown = Lines()
    folder = notices.NoticeFolder(shown, None, log_path=tmp_path / "s.log")
    for i in range(4):
        folder.handle(record("hubofhubs.x", f"w{i}"))
    folder.begin_run()
    folder.handle(record("hubofhubs.x", "w0"))
    assert shown.out.count("⚠ w0") == 2
    loud = Lines()
    notices.NoticeFolder(loud, None, verbosity=1, log_path=tmp_path / "v.log").handle(record("somelib", "full text. more"))
    assert "full text. more" in loud.out[0]


def test_an_unwritable_log_never_raises_and_the_hint_says_how_to_see_more(tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("x")
    shown = Lines()
    folder = notices.NoticeFolder(shown, None, log_path=blocked / "sub" / "s.log")
    folder.handle(record("hubofhubs.x", "one"))
    folder.finish()
    assert shown.out == ["⚠ one", "Details: run with -v"]


def test_the_first_sentence_is_cut_at_a_clause_or_a_word_and_a_log_path_is_under_the_state_folder():
    assert notices.short_text("First part. Second part") == "First part"
    assert notices.short_text("multi\nline") == "multi"
    long = "word " * 120
    assert notices.short_text(long, 40).endswith("…") and len(notices.short_text(long, 40)) <= 40
    assert notices.short_text("do this thing (see the docs for much more detail here)", 20) == "do this thing"
    assert str(notices.default_log_path({"XDG_STATE_HOME": "/state"})) == "/state/ahohs/session.log"
    assert str(notices.default_log_path({"HOME": "/h"})) == "/h/.local/state/ahohs/session.log"


# --- the words ----------------------------------------------------------------------------------------------------------------------------------

INTERNAL = ("harness", "agent_id", "step_id", "ask_id", "session_id", "deep", "orchestr", "solution_id", "payload", "traceback")


def test_every_word_is_sayable_has_no_long_dash_no_consumer_name_and_no_internal_word():
    for key, value in WORDS.items():
        assert not any(ch in value for ch in chr(0x2014) + chr(0x2013)), key
        assert not re.search(r"(?<![a-z])quest(?![a-z])", value, re.I), key
        assert not any(word in value.lower() for word in INTERNAL), key
        assert value.strip() and "  " not in value and not re.search(r"(?<!\{)\{\w+\}(?!\})", value), key
        if key.endswith("_one"):
            assert key[:-4] + "_other" in WORDS, key


def test_a_consumer_can_change_a_sentence_and_a_missing_key_never_shows_raw():
    strings.register_overrides({"polished.key.stop": "Cancel"})
    try:
        assert ("esc", "Cancel") in text.key_hints(busy=True, asking=False, stopped=False, runs=0, detail=False, structure=False)
    finally:
        strings.clear_overrides()
    with pytest.raises(KeyError):
        say("polished.not.a.key")
    assert say("polished.activity.waitingNotes", count=1) == "1 message waiting" and say("polished.activity.waitingNotes", count=3) == "3 messages waiting"
