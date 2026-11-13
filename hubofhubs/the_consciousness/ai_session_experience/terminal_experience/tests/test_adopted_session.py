"""The adopted arm (the vendored Mistral Vibe interface driven by the hub's session contract), headless: the adapter maps every event and control, each update has one home, a note typed while the
AI works is shown once as sent and then as taken up, a question is answered by a key and the approval reaches the harness, stop and resume, the closing, 80 and 56 columns, the lazy import boundary,
no environment reads and no consumer word. A scripted fake harness; no model, no network."""
import asyncio
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("textual")
pytest.importorskip("pydantic")
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Approve, Capabilities, Finished, Notice, Refuse, Review, RunStarted, Step, Steer, Stop, Usage, Waiting)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session import adapter as hub
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.app import make_app
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.session import AdoptedSession, Transcript
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView

ROOT = Path(__file__).resolve().parents[5]
FOLDER = Path(__file__).resolve().parents[1]


class Fake:
    """A harness that replays a script of events (a number sleeps, a callable runs) for each run, and records what the screen sent it."""
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
    return RunStarted(goal="goal", harness="stream", session_id="s1", **more)


def met(**more):
    return Finished(outcome="met", session_id="s1", **more)


def rows_of(app):
    return [strip.text.rstrip() for strip in app.screen._compositor.render_strips()]


def play(harness, keys=None, size=(80, 24), during=None, **more):
    """Run the arm's session on a headless screen of ``size`` and return the report, the transcript text and the rows of the screen at every sample."""
    held, samples = {}, []

    async def go():
        app = make_app()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.3)       # the screen has its first layout before the run starts
            transcript = Transcript()
            options = dict(clock=time.monotonic, tick=0.01, live=False, width=size[0], records=None, commands=None, segments=(), panels=(), command="", representative=None,
                           stop_limits=None, headless=True, ansi=False)
            options.update(more)

            def work():
                held["report"] = AdoptedSession().attending(app, harness, "goal", transcript, keys, "", options)
            thread = threading.Thread(target=work, daemon=True)
            thread.start()
            limit = time.monotonic() + 25
            while thread.is_alive() and time.monotonic() < limit:
                await pilot.pause(0.05)
                samples.append(rows_of(app))
                if during is not None:
                    await during(pilot, app)
            thread.join(2)
            await pilot.pause(0.15)
            samples.append(rows_of(app))
    asyncio.run(go())
    return held["report"], held["report"].text, samples


def feed(events):
    """The screen's events for each session event, from one adapter over one view."""
    view = SessionView()
    adapter = hub.ScreenAdapter(view)
    out = []
    for event in events:
        view.apply(event)
        out.append(adapter.translate(event))
    return view, adapter, out


# --- the adapter: every event ---------------------------------------------------------------------------------------------------------

def test_run_started_is_the_persons_goal_as_their_own_message_and_a_resumed_run_says_so():
    _, _, out = feed([RunStarted(goal="Fix  the\nnotes", harness="stream", session_id="s1")])
    assert out[0] == [hub.GoalSent("Fix the notes")]
    _, _, out = feed([RunStarted(goal="x", resumed=True)])
    assert out[0] == [hub.HubLine("resuming", "continuing the earlier session")]


def test_a_step_is_one_entry_that_later_events_of_its_step_id_update_in_place():
    _, adapter, out = feed([Step(step_id="s1", kind="run", label="date", state="running"), Step(step_id="s1", kind="run", state="done")])
    added, updated = out[0][0], out[1][0]
    assert type(added).__name__ == "HistoryEntryAdded" and type(updated).__name__ == "HistoryEntryUpdated"
    assert updated.previous is added.entry and updated.entry.id == added.entry.id == "s1"
    assert type(added.entry.state).__name__ == "RunningEffectState" and type(updated.entry.state).__name__ == "CompletedEffectState"
    assert updated.entry.title == "date" and len(adapter.entries) == 1        # the label stays, one entry for the step id


def test_each_kind_of_step_has_its_own_effect_and_each_state_its_own_state():
    kinds = {"read": "file_read", "edit": "file_edit", "run": "shell", "check": "shell", "tool": "tool", "delegate": "subagent"}
    _, _, out = feed([Step(step_id=k, kind=k, label=f"{k} x", state="done") for k in kinds])
    assert [str(o[0].entry.detail.kind) for o in out] == list(kinds.values())
    _, _, out = feed([Step(step_id="f", kind="run", label="false", state="failed", detail="exit 1"), Step(step_id="b", kind="tool", label="deploy x", state="blocked", detail="not allowed")])
    assert type(out[0][0].entry.state).__name__ == "FailedEffectState" and out[0][0].entry.state.error.message == "exit 1"
    assert type(out[1][0].entry.state).__name__ == "CancelledEffectState" and "not allowed" in out[1][0].entry.state.display.message


def test_a_helpers_step_names_the_helper_and_a_note_is_narration_unless_it_is_the_answer():
    _, _, out = feed([AgentStarted(agent_id="h1", task="write the tests"), Step(agent_id="h1", step_id="t", kind="edit", label="tests.txt", state="done")])
    assert out[1][0].entry.state.display.suffix == " ↳"      # the marker of a helper's rows: its name is said once, when it starts
    _, _, out = feed([Step(step_id="n1", kind="note", label="Looking at the notes"), Step(step_id="n2", kind="note", label="Now the plan"), Finished(outcome="met", report="All done.")])
    assert out[0] == [] and [type(i).__name__ for i in out[1]] == ["HistoryEntryAdded"] and out[1][0].entry.content[0].text == "Looking at the notes"
    _, _, out = feed([Step(step_id="n1", kind="note", label="Today is Wednesday, Nov..."), Finished(outcome="met", report="Today is Wednesday, November 11.")])
    assert out[1] == []        # the note was the beginning of the answer: shown once, in the closing


def test_agent_started_and_ended_are_child_sessions_with_their_state():
    _, _, out = feed([AgentStarted(agent_id="h1", task="write the tests", solution="notes"), AgentEnded(agent_id="h1", state="met"), AgentEnded(agent_id="h1", state="stopped"),
                      AgentEnded(agent_id="h1", state="unmet")])
    states = [type(o[0].child_session.status).__name__ for o in out]
    assert states == ["RunningSessionStatus", "IdleSessionStatus", "IdleSessionStatus", "FailedSessionStatus"]      # a stopped helper stays in the list (an archived one would leave it) and says it was stopped
    assert out[2][0].child_session.name.endswith("(stopped)")
    assert out[0][0].child_session.name == "write the tests" and out[0][0].child_session.agent_type == "notes"


def test_waiting_is_an_approval_with_its_preview_or_a_question_when_the_options_are_others():
    view, adapter, out = feed([Waiting(ask_id="a1", question="Run deploy?", risky="deploy", preview="creates deployed.txt")])
    entry = out[0][0].callback
    assert type(entry.detail).__name__ == "ApprovalCallbackDetail" and entry.callback_id == "a1" and entry.detail.reason == "Run deploy?"
    assert entry.detail.effect.input == {"preview": "creates deployed.txt"} and entry.detail.effect.tool_name == "deploy"
    _, adapter, out = feed([Waiting(ask_id="a2", question="Which one?", options=("blue", "green"))])
    assert type(out[0][0].callback.detail).__name__ == "UserInputCallbackDetail" and adapter.options_of("a2") == ("blue", "green")


def test_a_notice_and_a_review_are_quiet_hub_lines_and_a_stop_names_the_session_that_resumes():
    _, _, out = feed([Notice(kind="soft-limit"), Notice(kind="decision", decision="stop", reason="plateau"), Review(text="two corrections"), Finished(outcome="stopped", session_id="s9")])
    assert out[0][0].kind == "limit" and "Wrapping up" in out[0][0].text
    assert out[1][0].kind == "notice" and out[1][0].text.startswith("Hub decision: stop")
    assert out[2][0] == hub.HubLine("review", "Review: two corrections")
    assert not [h for entries in out for h in entries if getattr(h, "kind", "") == "stopped"]      # a stop is said once, in the closing


def test_a_note_sent_is_taken_up_by_the_harnesss_message_received_step():
    _, _, out = feed([Step(step_id="m1", kind="message-received", label="use the short name")])
    assert out[0] == [hub.NoteTakenUp("m1", "use the short name")]


def test_the_closing_is_the_answer_once_the_detail_one_outcome_line_and_the_resume_command_alone():
    view, adapter, _ = feed([begin(metric="checks passing", metric_before=1.0, solution="notes", milestone="ship"), Usage(cost_usd=0.21, calls=2, tokens=135),
                             Step(step_id="e", kind="edit", label="b.txt", state="done"),
                             met(report="All **done**.", changed=("b.txt",), metric_after=3.0, cost_usd=0.21)])
    closing = adapter.closing(100)
    assert closing.answer == "All **done**." and closing.state == "met"
    assert sum("Metric checks passing: before 1, after 3 (+2)" in row for row in closing.detail) == 1 and "Changed (1): b.txt" in closing.detail
    assert len(closing.outcome) == 1 and closing.outcome[0].startswith("✓ Goal met") and "$0.21" in closing.outcome[0] and "1 file changed" in closing.outcome[0]
    assert closing.resume == ("Continue this session later, in this folder:", "ahohs work --resume s1")
    assert closing.answer not in "\n".join(closing.detail + closing.outcome + closing.resume)


# --- the screen: one home, a note sent then taken up, the approval round trip, stop and resume ------------------------------------------

def test_a_step_has_one_row_on_the_screen_from_running_to_done():
    fake = Fake([[begin(), Step(step_id="s1", kind="run", label="date", state="running"), 0.4, Step(step_id="s1", kind="run", label="date", state="done"), 0.4, met(report="It is late.")]])
    rep, text, samples = play(fake)
    counts = [sum("date" in row for row in rows) for rows in samples]
    assert max(counts) == 1 and counts[-1] == 1 and rep.final.outcome == "met"


def test_a_note_typed_while_the_ai_works_is_shown_once_as_sent_and_then_as_taken_up():
    keys = ScriptedKeys()
    fake = Fake([[begin(), lambda sink: keys.press("line", "use the short name"), 0.6, Step(step_id="m1", kind="message-received", label="use the short name"), 0.6, met()]])
    rep, text, samples = play(fake, keys)
    assert [c.text for c in fake.controls if isinstance(c, Steer)] == ["use the short name"]
    mine = [[row for row in rows if "use the short name" in row] for rows in samples]
    assert all(len(rows) <= 1 for rows in mine)        # never two homes for the same note
    queued = [i for i, rows in enumerate(mine) if rows and "queued" in rows[0]]
    taken = [i for i, rows in enumerate(mine) if rows and "taken up" in rows[0]]
    assert queued and taken and max(queued) < min(taken)
    assert text.count("You: use the short name") == 1 and "Your note was taken up: use the short name" in text


@pytest.mark.parametrize("key,control", [("y", Approve), ("n", Refuse)])
def test_the_approval_screen_shows_what_will_change_and_a_key_answers_it(key, control):
    fake = Fake([[begin(), Waiting(ask_id="a1", question="Run deploy release 1.0?", risky="deploy", preview="creates deployed.txt in the folder"), 2.0, met()]])
    seen = {}

    async def during(pilot, app):
        if len(app.query("#approval-app")) and "pressed" not in seen:
            await pilot.pause(0.7)                   # the screen ignores a key in its first half second
            seen["rows"] = rows_of(app)
            await pilot.press(key)
            seen["pressed"] = True
    rep, text, samples = play(fake, during=during)
    asked = " ".join(seen["rows"])
    assert "Run deploy release 1.0?" in asked and "creates deployed.txt" in asked and re.search(r"y approve\s+n refuse", asked)
    assert [type(c) for c in fake.controls if isinstance(c, (Approve, Refuse))] == [control]
    assert not any("approval-app" in str(rows) for rows in samples[-2:]) and rep.final.outcome == "met"       # the input is back


def test_escape_stops_and_keeps_the_session_and_typing_resume_continues_it():
    fake = Fake([[begin(), 0.5, Finished(outcome="stopped", session_id="s1")], [begin(), Step(step_id="e", kind="edit", label="two.txt", state="done"), met(report="Done.")]])
    seen = {}

    async def during(pilot, app):
        attendance = app.attendance
        if attendance is None:
            return
        if attendance.running and "esc" not in seen:
            seen["esc"] = True
            await pilot.press("escape")
        elif attendance.view.status == "stopped" and "resume" not in seen:
            seen["resume"] = True
            await pilot.press(*"resume", "enter")
    rep, text, samples = play(fake, during=during)
    assert any(isinstance(c, Stop) for c in fake.controls) and fake.starts == [("goal", ""), ("goal", "s1")]
    assert [r.outcome for r in rep.runs] == ["stopped", "met"] and text.count("inished work is kept") == 1 and "ahohs work --resume s1" in text      # a stop is said once
    assert any("Type resume to continue, or quit to leave" in " ".join(rows) for rows in samples)      # while stopped, the key line says how to go on


# --- the closing on the screen, and the width -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("width", [80, 56])
def test_the_header_names_the_product_in_full_and_everything_fits_80_and_56_columns(width):
    fake = Fake([[begin(metric="checks", metric_before=1.0), Step(step_id="s1", kind="run", label="date", state="done"), Usage(cost_usd=0.2077, calls=2, tokens=135),
                  met(report="Today is **Wednesday, November 11, 2026**.\n\nI checked it with the date command.", metric_after=2.0, cost_usd=0.2077)]])
    rep, text, samples = play(fake, size=(width, 40))
    final = samples[-1]
    assert present.PRODUCT in final[0] and len(final[0]) <= width and all(len(row) <= width for rows in samples for row in rows)
    flat = " ".join(final)
    assert "Wednesday, November 11, 2026" in flat and "**" not in flat and "$0.21" in flat and flat.count("Metric checks: before 1, after 2") == 1
    assert "ahohs work --resume s1" in flat.replace("\n", " ") and re.search(r"Goal met", flat)
    resume = [line for line in text.splitlines() if "--resume" in line]
    assert len(resume) == 1 and resume[0] == "ahohs work --resume s1"        # one unbroken line in the text a person copies from


def test_who_the_ai_acts_for_is_in_the_header_and_the_structure_is_one_key_away():
    fake = Fake([[begin(solution="notes", milestone="ship the next release"), 1.5, met()]])
    seen = {}

    async def during(pilot, app):
        if app.attendance is not None and app.attendance.running and "Structure: notes" in " ".join(rows_of(app)) and "tab" not in seen:
            seen["tab"] = True
            await pilot.press("tab")
    rep, text, samples = play(fake, during=during, representative={"person": "Alex"})
    assert any("for Alex" in rows[0] for rows in samples)                                            # who the AI acts for, quietly, in the header
    assert any("Structure: notes [running]; 0 helpers (Tab shows the tree)" in " ".join(rows) for rows in samples)   # the solution the work serves, one quiet row from the first frame
    assert any("Acting for: Alex" in " ".join(rows) for rows in samples)                              # and the authority in force, one key (Tab) away


# --- the boundaries ---------------------------------------------------------------------------------------------------------------------

def test_importing_the_arm_loads_no_screen_library():
    code = ("import sys; import hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.session as s, "
            "hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.adapter as a; "
            "bad = [m for m in ('textual', 'rich', 'pydantic') if m in sys.modules]; sys.exit(1 if bad else 0)")
    done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": str(ROOT), "PATH": ""})
    assert done.returncode == 0, done.stderr[-400:]


def test_the_arm_declares_its_libraries_and_availability_can_name_a_missing_one():
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session.session import AdoptedSession as Arm
    modules = sorted(item.module for item in Arm.REQUIRES)
    assert modules == ["pydantic", "textual"]
    assert {item.extra for item in Arm.REQUIRES} == {"textual", "adopted_ui"}


def test_no_environment_read_and_no_consumer_word_in_the_adapter_the_binding_layer_or_the_vendored_copy():
    word = re.compile(r"(?<![A-Za-z])quest(?![a-z])", re.I)
    for path in sorted(FOLDER.rglob("*.py")):
        if "tests" in path.relative_to(FOLDER).parts or not any(part in ("adopted_session", "vendor") for part in path.relative_to(FOLDER).parts):
            continue
        text = path.read_text()
        assert not re.search(r"\b(environ|getenv|putenv)\b", text), path
        assert not word.search(text), path
        assert chr(0x2014) not in text and chr(0x2013) not in text, path       # the repository forbids dash characters, in the copy too


def test_the_vendored_copy_keeps_its_licence_and_a_readme_and_every_file_says_where_it_came_from():
    vendor = FOLDER / "vendor" / "mistral_vibe_ui"
    assert "Apache License" in (vendor / "LICENSE").read_text() and (vendor / "README.md").is_file()
    for path in sorted(vendor.rglob("*.py")):
        head = path.read_text().split('"""')[1] if path.read_text().startswith('"""') else ""
        assert "Mistral Vibe v2.26.1" in head or path.name == "__init__.py", path
