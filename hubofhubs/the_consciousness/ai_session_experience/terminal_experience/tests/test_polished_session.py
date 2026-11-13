"""The polished arm driven by a scripted fake harness that emits contract events: the queue rules, the closing, one home for each update, stop and resume, the consumer's
extension points. Headless (the screen runs without a terminal); no model, no network."""
import io
import tempfile
import time
from pathlib import Path

import pytest

pytest.importorskip("textual")
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Approve, Capabilities, Finished, Notice, RunStarted, Step, Steer, Stop, Usage, Waiting)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished import session as arm_module
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import PolishedApp
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.session import PolishedAttendance, PolishedSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import KITS, edit, read, report, turn
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys


class Fake:
    """A harness that replays a script of events (and hooks that press keys) for each run, and records what the screen sent it."""
    name = "fake"

    def __init__(self, runs, steer=True, accept=True):
        self.runs, self.accept = list(runs), accept
        self.capabilities = Capabilities(stop=True, resume=True, steer=steer, approve=True, steer_ack=True)
        self.controls, self.starts = [], []

    def start(self, goal, sink, resume_session_id=""):
        self.starts.append((goal, resume_session_id))
        done = None
        for item in self.runs.pop(0):
            if callable(item):
                item(sink)
            elif isinstance(item, (int, float)):
                time.sleep(item)
            else:
                sink(item)
                if isinstance(item, Finished):
                    done = item
        return done

    def control(self, control):
        self.controls.append(control)
        return True if isinstance(control, Stop) else self.accept


def begin(**more):
    return RunStarted(goal="goal", harness="fake", session_id="s1", **more)


def met(**more):
    return Finished(outcome="met", session_id="s1", **more)


def typed(keys, *lines):
    return lambda sink: [keys.press("line", line) for line in lines]


def taken(label):
    return Step(step_id="", kind="message-received", label=label, state="done")


def attend(harness, keys=None, arm=None, **options):
    out = io.StringIO()
    options.setdefault("live", False)
    report_ = (arm or PolishedSession()).attend(harness, "goal", out, keys or ScriptedKeys(), tick=0.01, width=100, **options)
    return report_, out.getvalue()


@pytest.fixture
def recorded(monkeypatch):
    """The snapshots the driver gave the screen and the text it put back in the prompt box."""
    snaps, boxed = [], []
    original = PolishedAttendance.snapshot

    def spy(self):
        found = original(self)
        snaps.append(found)
        return found
    monkeypatch.setattr(PolishedAttendance, "snapshot", spy)
    monkeypatch.setattr(PolishedApp, "set_prompt_text", lambda self, text: boxed.append(text))
    return snaps, boxed


# --- notes typed while the AI works -------------------------------------------------------------------------------------------------

def test_a_note_is_the_persons_own_line_counted_while_it_waits_and_shown_as_taken_up_once(recorded):
    snaps, _ = recorded
    keys = ScriptedKeys()
    fake = Fake([[begin(), typed(keys, "use the short name"), 0.25, taken("use the short name"), 0.25, met()]])
    rep, text = attend(fake, keys)
    assert [c.text for c in fake.controls if isinstance(c, Steer)] == ["use the short name"]
    assert "❯ You: use the short name" in text and text.count("Your note was taken up.") == 1
    assert "(queued" not in text and text.count("use the short name") <= 2        # the person's own line, no tag and no count, never restated
    queued = [s.queued for s in snaps]
    assert 1 in queued and queued[-1] == 0 and queued.index(1) < len(queued) - 1


def test_several_notes_no_run_took_up_become_one_next_message_in_the_order_typed():
    keys = ScriptedKeys()
    fake = Fake([[begin(), typed(keys, "first note", "second note"), 0.1, met()], [begin(), met()]], steer=False)
    rep, text = attend(fake, keys)
    assert fake.starts == [("goal", ""), ("first note\n\nsecond note", "s1")] and len(rep.runs) == 2
    assert "Sending your 2 waiting notes as one message." in text
    assert text.count("You: first note") == 1 and text.count("You: second note") == 1      # echoed when typed, not a second time when sent
    assert not [c for c in fake.controls if isinstance(c, Steer)]       # this worker cannot take one while it works


def test_a_message_the_worker_refused_is_kept_and_sent_with_the_next_one():
    keys = ScriptedKeys()
    fake = Fake([[begin(), typed(keys, "late thought"), 0.15, met()], [begin(), met()]], accept=False)
    rep, text = attend(fake, keys)
    assert fake.starts[1] == ("late thought", "s1") and len(fake.controls) >= 2      # offered again and again while it ran


def test_a_stopped_run_flushes_the_queue_into_a_new_message_that_continues_the_session():
    keys = ScriptedKeys()
    fake = Fake([[begin(), typed(keys, "after the stop"), lambda sink: keys.press("esc"), 0.1, Finished(outcome="stopped", session_id="s1")], [begin(), met()]], steer=False)
    rep, text = attend(fake, keys)
    assert any(isinstance(c, Stop) for c in fake.controls)
    assert fake.starts[1] == ("after the stop", "s1") and rep.runs[0].outcome == "stopped" and rep.final.outcome == "met"


def test_no_new_message_starts_after_an_error_and_the_notes_go_back_in_the_box(recorded):
    _, boxed = recorded
    keys = ScriptedKeys()
    fake = Fake([[begin(), typed(keys, "one", "two"), 0.1, Finished(outcome="failed", error="the worker broke", session_id="s1")], [begin(), met()]], steer=False)
    rep, text = attend(fake, keys)
    assert len(fake.starts) == 1 and rep.final.outcome == "failed"
    assert boxed == ["one\n\ntwo"] and "Your 2 notes are back in the box. Send them with your answer or clear them." in text


def test_a_note_is_never_sent_as_the_answer_to_a_question_the_person_has_not_read(recorded):
    _, boxed = recorded
    keys = ScriptedKeys()
    fake = Fake([[begin(), Waiting(ask_id="a1", question="Deploy the site?", preview="the live site"), typed(keys, "unrelated note"), 0.1,
                  Finished(outcome="stopped", session_id="s1", unseen=("unrelated note",))], [begin(), met()]])
    rep, text = attend(fake, keys)
    assert len(fake.starts) == 1 and boxed == ["unrelated note"] and not [c for c in fake.controls if isinstance(c, Approve)]
    assert "Your note is back in the box." in text and "Waiting for you: Deploy the site?" in text and "It will change: the live site" in text


def test_a_question_answered_by_y_sends_the_approval_and_a_later_note_is_an_ordinary_one():
    keys = ScriptedKeys().when("waiting", "line", "y")        # pressed once the screen shows the question
    fake = Fake([[begin(), Waiting(ask_id="a1", question="Deploy?"), 0.2, typed(keys, "now tidy"), 0.15, taken("now tidy"), met()]])
    rep, text = attend(fake, keys)
    assert [c.ask_id for c in fake.controls if isinstance(c, Approve)] == ["a1"] and [c.text for c in fake.controls if isinstance(c, Steer)] == ["now tidy"]
    assert len(fake.starts) == 1


def test_stop_then_resume_continues_the_same_session_and_says_so():
    keys = ScriptedKeys()
    fake = Fake([[begin(), lambda sink: (keys.press("esc"), keys.press("line", "resume")), 0.1, Finished(outcome="stopped", session_id="s1")], [begin(), met()]])
    rep, text = attend(fake, keys)
    assert fake.starts == [("goal", ""), ("goal", "s1")] and "resuming session s1" in text and "Stopping: finished work is kept" in text
    assert [r.outcome for r in rep.runs] == ["stopped", "met"]


# --- the closing: structured fields only, the metric once above the one closing line ---------------------------------------------------------------

def closing_index(rows):
    return max(i for i, row in enumerate(rows) if row.startswith(("✓ ", "✗ ", "◐ ", "■ ")) and " · " in row and ("Goal" in row or "Stopped" in row or "Failed" in row))


def test_the_answer_then_the_metric_once_then_the_detail_then_one_closing_line():
    fake = Fake([[begin(metric="checks passing", metric_before=1.0, solution="notes", milestone="ship"), Usage(cost_usd=0.0123, calls=3),
                  Step(step_id="e", kind="edit", label="b.txt", state="done"), met(report="All **done**.", changed=("b.txt",), metric_after=3.0)]])
    rep, text = attend(fake)
    rows = text.splitlines()
    metric = [i for i, r in enumerate(rows) if "before 1, after 3 (+2)" in r]
    assert len(metric) == 1 and rows[metric[0]] == "Metric checks passing: before 1, after 3 (+2)"
    answer = rows.index("All done.")       # the markers are taken out in a plain transcript
    closing = closing_index(rows)
    assert answer < metric[0] < closing and "Goal met" in rows[closing]
    assert "Changed (1): b.txt" in rows and "Served: notes | milestone: ship" in rows and sum("Goal met" in r for r in rows) == 1
    assert "$0.01" in rows[closing] and "3 calls" in rows[closing] and "1 file changed" in rows[closing] and not any(r.startswith("Cost and time") for r in rows)
    assert rows[-1].startswith("ahohs work --resume") and len(rows[-1].split()) >= 4       # the resume command is the last line, whole


def test_the_outcome_comes_from_the_structured_field_never_from_what_the_worker_wrote():
    fake = Fake([[begin(), Finished(outcome="failed", session_id="s1", error="the worker broke", report="Done! Everything worked and the goal was met.")]])
    rep, text = attend(fake)
    rows = text.splitlines()
    assert "Failed" in rows[closing_index(rows)] and "Reason: the worker broke" in rows
    fake = Fake([[begin(), met(report="Failed to do anything.")]])
    rep, text = attend(fake)
    assert "Goal met" in text.splitlines()[closing_index(text.splitlines())]


def test_the_cost_is_unknown_when_the_worker_gave_none_and_time_is_written_one_way():
    rep, text = attend(Fake([[begin(), met()]]))
    closing = text.splitlines()[closing_index(text.splitlines())]
    assert "cost unknown" in closing and "$0" not in closing
    import re
    assert re.search(r" · \d+:\d\d · ", closing) and not re.search(r"\d+m\d+s", text)


def test_off_a_terminal_there_are_no_escape_codes_and_on_one_the_closing_is_styled():
    rep, text = attend(Fake([[begin(), met(report="# Result\n\nA **bold** claim.")]]))
    assert "\x1b" not in text and "Result" in text and "# Result" not in text and "**bold**" not in text and "A bold claim." in text        # the markers are taken out, never shown
    rep, text = attend(Fake([[begin(), met(report="# Result\n\nA **bold** claim.")]]), live=True)
    assert "\x1b[" in text and "Goal met" in text and "**bold**" not in text and "# Result" not in text


def test_a_stopped_session_names_what_is_kept_and_the_command_that_resumes_it():
    rep, text = attend(Fake([[begin(), Finished(outcome="stopped", session_id="sess-9")]]), command="ahohs work")
    assert "Stopped" in text and text.count("Finished work is kept") == 1 and "ahohs work --resume sess-9" in text.splitlines()[-1]       # the command whole, alone on its last line


# --- the transcript keeps what finished, the panel what is happening now ----------------------------------------------------------------------------

def test_each_update_has_one_home_the_panel_while_it_runs_and_the_transcript_once_it_finished(recorded):
    snaps, _ = recorded
    fake = Fake([[begin(), Step(step_id="w", kind="edit", label="work.txt", state="running"), AgentStarted(agent_id="h1", task="check the tests"), 0.3,
                  Step(step_id="w", kind="edit", label="work.txt", state="done"), AgentEnded(agent_id="h1", state="met"), 0.3, met(changed=("work.txt",))]])
    rep, text = attend(fake)
    shown = [any("work.txt" in row for row, _ in s.rows) for s in snaps]
    assert True in shown and shown[-1] is False and shown.index(True) < len(shown) - shown[::-1].index(True)        # in the panel while running, gone when finished
    rows = text.splitlines()
    assert sum("Edited work.txt" in r for r in rows) == 1                # the transcript has the finished step once
    assert not [r for r in rows if "Helper started" in r] and any("Helper: check the tests" in r for r in rows)        # the transcript names the helper once, as the heading of its rows, and says its ending
    assert any("Helper finished: check the tests" in r for r in rows) and any(("check the tests" in row) for s in snaps for row, _ in s.rows)


def test_a_clock_is_shown_after_three_seconds_of_waiting_and_not_before(recorded):
    snaps, _ = recorded
    ticks = iter(range(0, 10000))
    rep, text = attend(Fake([[begin(), Step(step_id="r", kind="run", label="slow", state="running"), 0.3, Step(step_id="r", kind="run", label="slow", state="done"), met()]]),
                       clock=lambda: next(ticks) * 0.5)
    waits = [s.waited for s in snaps if s.busy]
    assert waits and max(w for w in waits if w is not None) >= 3 and min(w for w in waits if w is not None) < 3


def test_a_warning_notice_of_the_contract_is_one_line_and_the_decision_lines_are_the_hubs():
    fake = Fake([[begin(), Notice(kind="soft-limit"), Notice(kind="decision", decision="stop", reason="plateau"), met()]])
    rep, text = attend(fake)
    assert sum("Wrapping up:" in r for r in text.splitlines()) == 1 and "Hub decision: stop, the last round gained almost nothing" in text


# --- the consumer's extension points -----------------------------------------------------------------------------------------------------------------------

def test_a_consumer_supplies_its_own_metric_lines_and_a_save_hook_and_neither_can_break_the_run():
    saved = []
    arm = PolishedSession(metric_rows=lambda view: ["Speed: 2 → 4 (measured)", "Accuracy: 0.5 → 0.9 (measured)"], persist=lambda view, done: saved.append((view.goal, done.outcome)))
    rep, text = attend(Fake([[begin(metric="x", metric_before=1.0), met(metric_after=2.0)]]), arm=arm)
    rows = text.splitlines()
    assert rows.index("Speed: 2 → 4 (measured)") < closing_index(rows) and "Accuracy: 0.5 → 0.9 (measured)" in rows and not any(r.startswith("Metric x") for r in rows)
    assert saved == [("goal", "met")]
    broken = PolishedSession(metric_rows=lambda view: 1 / 0, persist=lambda view, done: 1 / 0)
    rep, text = attend(Fake([[begin(), met()]]), arm=broken)
    assert rep.final.outcome == "met" and "Goal met" in text


def test_a_consumers_command_and_segment_and_panel_rows_reach_the_screen_through_the_shared_options(recorded):
    snaps, _ = recorded
    keys = ScriptedKeys()
    said = []
    fake = Fake([[begin(), Step(step_id="x", kind="run", label="go", state="running"), typed(keys, "/tag blue"), 0.3, met()]])
    rep, text = attend(fake, keys, commands={"tag": lambda rest: said.append(rest) or f"tagged {rest}"}, segments=[lambda view: "plan: basic"],
                       panels=[lambda view: ["context: 3 sources"]])
    assert said == ["blue"] and "tagged blue" in text
    assert any("plan: basic" in s.head for s in snaps) and any(("context: 3 sources", "step") in s.rows for s in snaps)


# --- the same screen on any worker, and the interactive prompt ---------------------------------------------------------------------------------------

def folder_kit(name, turns):
    folder = tempfile.mkdtemp(prefix="pol-")
    Path(folder, "a.txt").write_text("alpha\n")
    return KITS[name](folder, turns, pause=0.0)


def test_the_same_script_on_two_workers_gives_the_same_rows_and_outcome():
    rows = []
    for name in ("loop", "stream"):
        kit = folder_kit(name, [turn(read("a.txt")), turn(edit("b.txt")), turn(report("All done."))])
        rep, text = attend(kit.harness)
        rows.append(([(e.kind, e.label) for e in rep.events if isinstance(e, Step) and e.state == "done" and e.kind != "note"], rep.final.outcome, "Changed (1): b.txt" in text))
    assert rows[0] == rows[1] and rows[0][1] == "met" and rows[0][2]


def test_the_interactive_prompt_asks_for_a_goal_runs_it_and_leaves_on_quit():
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.work import WorkTerminal
    fake = Fake([[begin(), met(report="Done it.")]])
    out = io.StringIO()
    terminal = PolishedSession().work(lambda name: fake, out, lines=["do it", "/quit"], harness="fake", names=("fake",))
    assert isinstance(terminal, WorkTerminal) and len(terminal.reports) == 1 and fake.starts == [("do it", "")]
    assert "Type a goal and press Enter" in out.getvalue() and "Goal met" in out.getvalue()


def test_the_arm_is_registered_needs_only_the_screen_library_and_stands_aside_without_it(monkeypatch):
    from hubofhubs.the_self.assembler import availability
    from hubofhubs.the_self.assembler.resolution import HUB
    assert availability.unmet(HUB, "terminal-session", "polished_session", {}, {}) == ""
    monkeypatch.setitem(__import__("sys").modules, "textual", None)
    assert "textual" in availability.unmet(HUB, "terminal-session", "polished_session", {}, {}).lower()
    assert arm_module.PolishedSession.REQUIRES and "polished_session" in HUB.names("terminal-session")
