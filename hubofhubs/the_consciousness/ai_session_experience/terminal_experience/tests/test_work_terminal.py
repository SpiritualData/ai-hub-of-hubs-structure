"""The hub's own parts of the terminal (``ahohs work``): structure on request, ceilings, the soft limit, the stop decision, follow-ups, a harness switch, the no-goal prompt,
the Representative, and the helpers behind them. Scripted harnesses only: no model, no network."""
import io
import json
import tempfile
from pathlib import Path

import pytest

from hubofhubs.the_consciousness.ai_session_experience.session_adapters import progress_events
from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, Notice, Usage, event_from_dict
from hubofhubs.the_consciousness.ai_session_experience.session_harnesses import Briefed, Tailed
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import (
    decide, delegate, edit, loop_kit, outside, read, refuse_round, report, soft_limit, stream_kit, turn)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import frame
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.work import HARNESSES, WorkTerminal, dollars_of, seconds_of
from hubofhubs.the_world.tools.deep import ProgressEvent

TABLES = {"solutions": [{"solution_id": "alpha", "name": "Alpha", "purpose": "Do alpha.", "approach": "Alpha way.", "out_of_scope": "", "authoritative_metric_id": "",
                         "selected": "", "milestones": "", "problem_ids": "", "ideal_ids": "", "delegates_to": ""}],
          "problems": [], "ideals": [], "implementations": [], "metrics": [], "results": []}


def folder():
    path = tempfile.mkdtemp(prefix="work-")
    Path(path, "a.txt").write_text("alpha\n")
    return path


def attend(kit, keys=None, **options):
    out = io.StringIO()
    return LiveSession().attend(kit.harness, "go", out, keys or ScriptedKeys(), tick=0.01, live=False, width=100, **options), out.getvalue()


def work(kits, lines, **options):
    out = io.StringIO()
    names = list(kits)
    terminal = LiveSession().work(lambda name: kits[name].harness, out, lines=lines, harness=names[0], names=names, tick=0.01, live=False, width=100, **options)
    return terminal, out.getvalue()


def test_new_events_round_trip_and_the_runner_ticks_become_them():
    for event in (Notice(kind="decision", decision="stop", reason="resume_limit", items=("a",)), Usage(cost_usd=1.0, ceiling_usd=5.0, ceiling_seconds=60.0),
                  Finished(outcome="met", end_reason="x", outside=("o",), spend_usd=0.1)):
        assert event_from_dict(json.loads(json.dumps(event.to_dict()))) == event
    soft = progress_events(ProgressEvent(type="status", text="limit", data={"phase": "soft_limit"}))
    assert [e.kind for e in soft] == ["soft-limit"]
    resume = progress_events(ProgressEvent(type="status", text="again", data={"phase": "hub_resume", "reason": "code_finding"}))
    assert (resume[0].decision, resume[0].reason) == ("continue", "code_finding")
    spend = progress_events(ProgressEvent(type="tokens", data={"cost_usd": 0.5, "turns": 3, "ceiling_usd": 20.0, "ceiling_seconds": 3600.0}))
    assert (spend[0].cost_usd, spend[0].calls, spend[0].ceiling_usd) == (0.5, 3, 20.0)
    assert progress_events(ProgressEvent(type="status", text="reading", data={"phase": "other"})) == []


def test_structure_is_collapsed_until_asked_and_opens_one_solution():
    keys = ScriptedKeys()
    kit = stream_kit(folder(), [turn(delegate("[alpha] check", turn(edit("x.txt"), report("ok")))),
                                turn(read("a.txt"), hook=lambda: [keys.press(k) for k in ("tree", "open")]), turn(report("Done."))], frame={"solution": "alpha"})
    rep, text = attend(kit, keys, records=TABLES)
    assert "purpose: Do alpha." in text and text.index("structure (") < text.index("purpose:")
    assert rep.view.structure_compact.startswith("structure: Alpha")
    assert "\x1b[" not in text


def test_a_tree_key_with_nothing_to_show_says_so_once():
    keys = ScriptedKeys()
    kit = stream_kit(folder(), [turn(read("a.txt"), hook=lambda: keys.press("tree")), turn(report("Done."))])
    rep, text = attend(kit, keys)
    assert text.count("No solution is named for this run yet") == 1


def test_ceilings_show_against_spend_and_time_and_only_when_there_are_some():
    rep, text = attend(stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))], limits=(5.0, 1800.0)))
    assert "of $5.00" in frame(rep.view, 100)[0] and "of 30:00" in frame(rep.view, 100)[0]
    bare, _ = attend(stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))]))
    assert " of " not in frame(bare.view, 100)[0]


def test_soft_limit_decision_and_the_end_of_the_run_are_one_line_each():
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(soft_limit(), decide("code_finding")), turn(refuse_round("resume_limit"), outside("wrote x elsewhere"), report("Done."))],
                     limits=(0.01, 1800.0))
    rep, text = attend(kit)
    assert text.count("wrapping up:") == 1 and "spend ceiling" in text
    assert "hub decision: go on, the check found something to fix" in text and "hub decision: stop, it already went round once more" in text
    assert "Left: the hub chose not to go round again" in text and "Outside the folder (report only" in text and "ahohs work --resume sess-" in text


def test_a_follow_up_continues_the_session_and_a_switch_starts_a_new_one_with_a_recap():
    stream = stream_kit(folder(), [turn(edit("one.txt")), turn(report("First."))])
    stream.runner.followups = [[turn(edit("two.txt"), report("Second."))]]
    loop = loop_kit(folder(), [turn(edit("l.txt"), report("Loop done."))])
    terminal, text = work({"stream": stream, "loop": loop}, ["start", "more", "/harness nope", "/harness loop", "other", "/quit"])
    first, second, third = terminal.reports
    assert second.events[0].resumed and second.final.session_id == first.final.session_id and second.final.report == "Second."
    assert third.events[0].harness == "loop" and not third.events[0].resumed and loop.trace.heard(0, "Earlier in this conversation")
    assert "no harness named 'nope'" in text


def test_with_no_goal_it_asks_and_a_blank_line_runs_nothing():
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(report("Done."))])
    terminal, text = work({"stream": kit}, ["", "  ", "do it", "/quit"])
    assert text.startswith("Type a goal") and len(terminal.reports) == 1 and terminal.reports[0].view.goal == "do it"


def test_extra_commands_segments_panels_and_a_front_door_are_the_bindings_of_a_consumer():
    kit = stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))])
    terminal, text = work({"stream": kit}, ["/mine 3", "/ask what", "go", "/quit"], commands={"mine": lambda rest: "mine got " + rest}, front_door=lambda t: "door: " + t,
                          segments=[lambda view: "seg"], panels=[lambda view: ["panel row"]])
    assert "mine got 3" in text and "door: what" in text
    assert frame(terminal.reports[0].view, 100)[0].endswith("| seg") and "panel row" in frame(terminal.reports[0].view, 100)


def test_the_representative_is_named_listed_switched_and_its_stop_limits_reach_the_run():
    from hubofhubs.the_consciousness.representatives.representatives import DeclaredAuthority
    reps = DeclaredAuthority({"alex": {"authority": {"allow": ["files"]}, "preferences": {"iteration": {"one_pass": True}}}, "sam": {}})
    kit = stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))])
    out = io.StringIO()
    terminal = WorkTerminal(lambda name: kit.harness, out, lines=["/as", "/as nobody", "/who", "/as sam", "go", "/quit"], harness="stream", names=("stream",), tick=0.01, live=False,
                            represent=reps.represent, people=("alex", "sam"), person="alex")
    assert terminal.stop_inputs()["stated"] == {"one_pass": True}
    terminal.run()
    text = out.getvalue()
    assert "* alex" in text and "no representative named 'nobody'" in text and "worker categories allowed: files" in text and "now acting for sam" in text
    assert terminal.reports[0].view.acting_for == "sam" and terminal.stop_inputs()["stated"] == {}
    bare = stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))])
    rep, plain = attend(bare)
    assert "for " not in frame(rep.view, 100)[0].split("|")[-1] and "acting for" not in plain


def test_the_words_the_header_and_the_resume_command_use():
    assert hub_lines.status_segment(42, 0.0123, 20.0, 14400.0) == ("0:42 of 4:00:00", "$0.0123 of $20.00")
    assert hub_lines.status_segment(42, None, None, None) == ("0:42", "cost unknown")
    assert "42 percent of the spend ceiling" in hub_lines.soft_limit_line(10, 0.42, 1.0, 3600.0)
    assert hub_lines.reason_words("plateau") == "the last round gained almost nothing"
    assert hub_lines.resume_command("stream", "abc") == "ahohs work --resume abc --harness stream"
    assert hub_lines.left_line("met", "", "", 0) == ""
    assert seconds_of("90s") == 90 and seconds_of("2h") == 7200 and seconds_of("3") == 180 and seconds_of("unlimited") is None
    assert dollars_of("$5") == 5.0 and dollars_of("unlimited") is None
    for bad in ("0", "x"):
        with pytest.raises(ValueError):
            seconds_of(bad)
    assert set(HARNESSES) == {"native", "stream", "loop"}


def test_tailed_reads_the_steps_from_the_sessions_record_and_leaves_earlier_lines_alone():
    directory = Path(tempfile.mkdtemp(prefix="tail-"))
    record = directory / "s.jsonl"
    record.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "old", "name": "Read", "input": {"file_path": "old.txt"}}]}}) + "\n")
    seen = []

    class Inner:
        name, capabilities = "stream", None

        def start(self, goal, sink, resume_session_id=""):
            with record.open("a") as handle:
                handle.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Edit", "input": {"file_path": f"{directory}/new.txt"}}]}}) + "\n")
            return Finished(outcome="met")

        def control(self, control):
            return False
    Tailed(Inner(), lambda resume, began: str(record), root=str(directory)).start("go", seen.append, resume_session_id="s")
    assert [e.label for e in seen if getattr(e, "kind", "") == "edit"] == ["new.txt"] and not [e for e in seen if getattr(e, "label", "") == "old.txt"]


def test_briefed_adds_text_the_screen_does_not_show():
    got = []

    class Inner:
        name, capabilities = "stream", None

        def start(self, goal, sink, resume_session_id=""):
            got.append(goal)
            from hubofhubs.the_consciousness.ai_session_experience.session_events import RunStarted
            sink(RunStarted(goal=goal))
            return Finished(outcome="met")
    shown = []
    Briefed(Inner(), "NOTE").start("do it", shown.append)
    assert got == ["do it\n\nNOTE"] and shown[0].goal == "do it"


def test_the_arrow_and_tab_keys_become_tree_keys(monkeypatch):
    import os
    import pty
    import time
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import TtyKeys
    master, slave = pty.openpty()
    pressed = []
    keys = TtyKeys(stream=os.fdopen(slave, "r"))
    keys.attach(lambda token, text="": pressed.append(token))
    try:
        os.write(master, b"\t\x1b[B\x1b[C\x1b[D\x1b[A?")
        time.sleep(0.5)
    finally:
        keys.detach()
    assert [t for t in pressed if t != "typing"] == ["tree", "down", "open", "close", "up", "help"]


def test_bare_ahohs_without_a_terminal_prints_the_short_help_and_work_needs_a_goal(capsys):
    from hubofhubs.the_self.assembler.cli import main
    assert main([]) == 0
    assert "work" in capsys.readouterr().out
    assert main(["work", "--folder", "."]) == 2
    assert main(["work", "--tier", "nonsense", "x"]) == 2
