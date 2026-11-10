"""The session contract, its adapters and the reference terminal, on a scripted loop and a fake of the stream runner: no model, no network."""
import io
import tempfile
from pathlib import Path

import pytest

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession, main
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import KITS, delegate, edit, read, report, turn, use
from hubofhubs.the_consciousness.ai_session_experience.session_adapters import LoopLines, StreamJson, progress_events
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, Approve, Finished, RunStarted, Step, Steer, Stop, Usage, Waiting, control_from_dict, event_from_dict)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_world.tools.deep import ProgressEvent

KITNAMES = ("loop", "stream")


def attend(kit, keys, live=False):
    out = io.StringIO()
    return LiveSession().attend(kit.harness, "do it", out, keys, tick=0.01, live=live, width=100), out.getvalue()


def kit_of(name, turns, **kw):
    folder = tempfile.mkdtemp(prefix="live-")
    Path(folder, "a.txt").write_text("alpha\n")
    return KITS[name](folder, turns, **kw)


def test_every_event_and_control_survives_a_round_trip():
    for event in (RunStarted(goal="g", solution="s", metric_before=1.0), Step(kind="edit", label="a.py", state="blocked"), Waiting(preview="x"),
                  Usage(cost_usd=0.1), Finished(outcome="met", changed=("a.py",), blocked=("b: no",), metric_after=2.0)):
        assert event_from_dict(event.to_dict()) == event
    for control in (Stop(agent_id="h"), Steer(text="t", message_id="m"), Approve(ask_id="a")):
        assert control_from_dict(control.to_dict()) == control
    with pytest.raises(ValueError):
        event_from_dict({"type": "nope"})


def test_the_loop_lines_and_the_stream_lines_become_steps():
    lines = LoopLines()
    got = [e for text in ("call 1: EDIT app.py ok", "call 2: check failed", "review: 2 correction(s)") for e in lines.events(text)]
    assert [(e.type, getattr(e, "kind", "")) for e in got] == [("step", "edit"), ("step", "check"), ("review", "")]
    stream = StreamJson()
    task = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Task", "input": {"description": "tests"}}]}}
    inner = {"type": "assistant", "parent_tool_use_id": "t1", "message": {"content": [{"type": "tool_use", "id": "t2", "name": "Edit", "input": {"file_path": "x.py"}}]}}
    events = stream.events(task) + stream.events(inner)
    assert [e.type for e in events] == ["agent-started", "step", "step"] and events[2].agent_id == "t1" and "x.py" in stream.changed
    assert progress_events(ProgressEvent(type="decision", text="ok?", decision_id="d1"))[0].ask_id == "d1"


@pytest.mark.parametrize("name", KITNAMES)
def test_stop_keeps_the_work_and_resume_finishes_without_repeating(name):
    keys = ScriptedKeys()
    kit = kit_of(name, [turn(edit("one.txt")), turn(edit("two.txt"), hook=lambda: (keys.press("esc"), keys.press("line", "resume"))),
                        turn(edit("three.txt"), report("done"))])
    got, text = attend(kit, keys)
    assert [r.outcome for r in got.runs] == ["stopped", "met"] and got.runs[0].session_id
    edits = [e.label for e in got.events if isinstance(e, Step) and e.kind == "edit" and e.state == "done"]
    assert sorted(edits) == ["one.txt", "three.txt", "two.txt"] and len(edits) == 3
    assert "\x1b" not in text and "Changed (3)" in text


@pytest.mark.parametrize("name", KITNAMES)
def test_a_steer_is_shown_sent_then_taken_up_and_reaches_the_next_call(name):
    keys = ScriptedKeys()
    kit = kit_of(name, [turn(read("a.txt"), hook=lambda: keys.press("line", "use the short name")), turn(edit("b.txt"), report("ok"))])
    got, text = attend(kit, keys)
    assert any(isinstance(c, Steer) and ok for c, ok in got.controls)
    assert "you: use the short name" in text and "taken up" in text
    assert kit.trace.heard(1, "use the short name") and not kit.trace.heard(0, "use the short name")


@pytest.mark.parametrize("name", KITNAMES)
@pytest.mark.parametrize("answer,ran", (("y", True), ("n", False)))
def test_a_risky_step_waits_and_runs_only_when_approved(name, answer, ran):
    keys = ScriptedKeys()
    seen = {}

    def react(event):
        if event.type == "waiting":
            seen["before"] = Path(kit.folder, "deployed.txt").exists()
            keys.press("line", answer)
    keys.react = react
    kit = kit_of(name, [turn(use("deploy", "v1")), turn(report("done"))])
    got, text = attend(kit, keys)
    assert seen["before"] is False and Path(kit.folder, "deployed.txt").exists() is ran
    assert ("Blocked or refused" in text) is (not ran)


def test_helpers_show_with_their_parent_and_a_helper_can_be_stopped_alone_on_the_stream():
    keys = ScriptedKeys().when("agent-started", "line", "/stop tests")
    kit = kit_of("stream", [turn(delegate("write the tests", turn(*[edit(f"t{i}.txt") for i in range(8)], report("x")))), turn(report("done"))], pause=0.05)
    got, text = attend(kit, keys)
    ended = [e for e in got.events if isinstance(e, AgentEnded)]
    assert ended and ended[0].state in ("failed", "stopped") and got.final.outcome == "met" and "`- write the tests" in text


def test_a_terminal_redraws_in_place_and_a_pipe_gets_plain_lines():
    kit = kit_of("stream", [turn(read("a.txt")), turn(report("done"))])
    got, text = attend(kit, ScriptedKeys(), live=True)
    assert "\x1b[" in text and "Done: the goal was met" in text


def test_the_demo_runs_with_no_model(capsys):
    assert main(["--demo", "stream", "--slow", "0"]) == 0
    assert "Done: the goal was met" in capsys.readouterr().out
    assert main([]) == 0
