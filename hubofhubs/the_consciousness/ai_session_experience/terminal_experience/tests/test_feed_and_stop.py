"""The feed, the stop and the words of the terminal views (revision 5 of the presentation metric): the agent's task-list tools are never drawn, a command that did not work is one muted
plain line, steps of one kind are one summary row, a helper is named once, a stop at a ceiling is said once, every label starts with a capital, a refusal never reaches a screen as the
harness's own text, and a view that cannot draw an event never ends the run."""
import io
import json

from hubofhubs.the_consciousness.ai_session_experience.session_adapters import StreamJson
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    BOOKKEEPING_TOOLS, AgentEnded, AgentStarted, Finished, Notice, RunStarted, Step, Usage, is_bookkeeping)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import (
    bookkeeping, delegate, edit, fail_read, fail_run, hard_stop, read, report, stream_kit, turn)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView, event_line, frame, report as closing


def test_the_agents_task_list_tools_are_never_a_step():
    stream = StreamJson("")
    use = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "TaskCreate", "input": {"subject": "plan"}}]}}
    result = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": False}]}}
    assert stream.events(use) == [] and stream.events(result) == []
    assert {"TaskCreate", "TaskUpdate", "TaskList"} <= set(BOOKKEEPING_TOOLS) and is_bookkeeping("tool", "TaskUpdate 3") and not is_bookkeeping("run", "TaskCreate")
    view = SessionView()
    view.apply(Step(step_id="x", kind="tool", label="TaskCreate", state="done"))       # a harness that emits one anyway: the view leaves it out
    assert not view.steps and event_line(Step(step_id="x", kind="tool", label="TaskCreate", state="done"), view) == ""


def test_a_failed_command_is_one_muted_plain_line_and_a_repeat_is_counted():
    command = 'cd /some/folder; grep -rhoiE "(because|pattern)" . | sort | uniq -c'
    step = Step(step_id="c", kind="run", label=command, state="failed")
    line = present.step_line(step, color=True)
    assert present.plain(line) == "○ Tried to search the text, did not work" and line.startswith(present.GREY) and "grep" not in line and "..." not in line
    assert "(3 times)" in present.step_line(step, times=3) and "again" in present.step_line(step, times=3)
    assert command in present.step_line(step, detail=True)                          # the detail view keeps the command
    view = SessionView()
    for n in range(3):
        view.apply(Step(step_id=f"c{n}", kind="run", label="for f in a b; do echo $f; done", state="running"))
        view.apply(Step(step_id=f"c{n}", kind="run", label="", state="failed"))
    assert view.failures == {"go through several files": 3}
    rows = [r for r in frame(view, 80) if "did not work" in r]
    assert rows == [] or len(rows) == 1                                                # one row for the three in the panel


def test_a_refused_command_is_one_plain_line_whatever_the_client_and_the_raw_text_stays_in_the_detail():
    quoted = Step(step_id="q", kind="run", label='find . -name "*.md"', state="blocked", detail="Quoted text in this command can't be checked before it runs")
    outside = Step(step_id="o", kind="run", label="head -n 5 /elsewhere/goals.yaml", state="blocked", detail="head in '/elsewhere/goals.yaml' was blocked")
    assert present.plain(present.step_line(quoted)) == "○ Skipped a command that could not be checked"
    assert present.plain(present.step_line(outside)) == "○ Skipped a command that was not allowed in this folder"
    assert "elsewhere" not in present.step_line(outside) and "Refused" not in present.step_line(outside)
    assert quoted.detail.startswith("Quoted text")


def test_steps_of_one_kind_are_one_row_with_short_subjects_and_a_helper_is_named_once():
    view = SessionView()
    rows = []
    events = [RunStarted(goal="g"), AgentStarted(agent_id="h", task="Find one interesting finding in the garden notes. Then summarise."),
              *[Step(step_id=f"r{n}", kind="read", label=f"/home/someone/.claude/projects/x/memory/note_{n}.md", state="done") for n in range(5)],
              Step(agent_id="h", step_id="a", kind="read", label="notes/one.md", state="done"), Step(agent_id="h", step_id="b", kind="read", label="notes/two.md", state="done"),
              Step(step_id="e", kind="edit", label="out.txt", state="done"), AgentEnded(agent_id="h", state="met"), Finished(outcome="met", report="Done.")]
    for event in events:
        view.apply(event)
        row = event_line(event, view, True)
        if row:
            rows.append(row)
    text = "\n".join(rows)
    assert "✓ Read 5 files: note_0.md, note_1.md and 3 more" in text and "/home/" not in text           # a count and short subjects, never a full path
    assert text.count("Find one interesting finding in the…") == 2 and "↳ Helper: Find one interesting finding in the…" in text   # the heading, and the ending; cut at a word
    assert "↳ ✓ Read 2 files: one.md, two.md" in text and "· Find one" not in text                    # a helper's rows carry the marker, not its name


def test_failed_reads_are_one_muted_summary_never_one_line_each():
    view = SessionView()
    rows = [event_line(Step(step_id=f"m{n}", kind="read", label=f"missing/file_{n}.md", state="failed"), view, True) for n in range(4)]
    rows.append(event_line(Step(step_id="ok", kind="read", label="a.md", state="done"), view, True))
    rows.append(event_line(Finished(outcome="met"), view, True))
    assert "\n".join(rows).count("Skipped 4 files that were not available") == 1 and "Could not read" not in "\n".join(rows)


def test_paths_are_shortened_and_names_are_cut_at_a_word():
    assert present.shorten_path("/home/someone/.claude/projects/x/memory/feedback_one.md") == "…/x/memory/feedback_one.md" or len(present.shorten_path("/home/someone/.claude/projects/x/memory/feedback_one.md")) <= 40
    assert all(len(present.shorten_path(p)) <= 41 for p in ("stories/psychic_journeys/human_context/from_quest/2026-11-10-note_3d628ed2e8d5.md", "/home/a/b/c/d/e/f.md", "short.md"))
    assert present.clip_words("Find one interesting finding in psychic practice files", 30) == "Find one interesting finding…"
    assert present.clip_words("Short name", 30) == "Short name"
    assert present.helper_name("Find an interesting pattern. Then do more.") == "Find an interesting pattern"


def test_a_stop_at_a_ceiling_is_said_once_with_what_is_kept_how_to_continue_and_how_to_raise_it():
    view = SessionView(command="ahohs work")
    for event in (RunStarted(goal="g", session_id="s9"), Usage(ceiling_usd=20.0), Notice(kind="hard-limit", reason="spend"), AgentEnded(agent_id="h", state="stopped"),
                  Finished(outcome="stopped", session_id="s9", end_reason="stopped_at_hard_limit:spend", error="The run was stopped at its hard limit (spend). Work already finished is kept; resume session s9")):
        view.apply(event)
    feed = [event_line(Notice(kind="hard-limit", reason="spend"), view, True), event_line(AgentEnded(agent_id="h", state="stopped"), view, True)]
    assert feed == ["", ""]                                                             # nothing in the feed says it: the closing does
    text = "\n".join(closing(view))
    assert text.count("Stopped at the spend limit") == 1 and text.count("Finished work is kept") == 1 and "--max-spend" in text and text.splitlines()[-1] == "ahohs work --resume s9"
    assert "Left:" not in text and "was stopped" not in text and "Handed off" not in text


def test_every_label_of_the_shared_words_starts_with_a_capital():
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import HELP_ROWS
    for text in list(present.TEXT.values()) + list(HELP_ROWS):
        assert text[:1].isupper() or not text[:1].isalpha(), text
    assert present.key_name("alt+d") == "Alt+D" and present.key_name("pgup/pgdn") == "PgUp/PgDn" and present.key_name("y/n") == "Y/N"
    lines = frame(SessionView(status="running"), 80)
    assert lines[-2] == present.TEXT["keys_default"]


def test_the_agents_block_has_a_heading_the_state_first_and_no_cut_word():
    view = SessionView()
    view.apply(RunStarted(goal="g"))
    view.apply(AgentStarted(agent_id="h", task="Find one interesting finding in psychic practice files and then report what it found"))
    for width in (56, 80, 120):
        rows = frame(view, width, transcript=True)
        assert "Agents" in rows and all(len(r) <= width - 1 for r in rows)
        agent = rows[rows.index("Agents") + 1]
        assert agent.index("Running") < agent.index("Find") and (agent.rstrip().endswith("…") or "report what it found" in agent)
        assert not any("..." in r for r in rows)


def test_a_view_that_cannot_draw_an_event_logs_it_once_and_the_run_goes_on(tmp_path, monkeypatch):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import live

    def broken(event, view, panel=False):
        raise AttributeError("module present has no attribute 'helper_marker'")
    monkeypatch.setattr(live, "event_line", broken)
    kit = stream_kit(str(tmp_path), [turn(read("a.txt"), edit("b.txt"), report("The answer arrives."))])
    kit.harness.root = str(tmp_path)
    out = io.StringIO()
    got = LiveSession().attend(kit.harness, "do it", out, ScriptedKeys(), live=False, width=100)
    assert got.final.outcome == "met" and "The answer arrives." in out.getvalue()      # the session went on and the answer still arrived
    log = (tmp_path / ".ahohs" / "render_errors.log").read_text()
    assert log.count("Could not draw") == 1 and "AttributeError" in log                # written once, with the trace, in the run's own folder


def test_a_scripted_noisy_run_reads_cleanly_end_to_end(tmp_path):
    helper = delegate("Find one interesting finding in the garden notes.", turn(read("a.txt"), bookkeeping("TaskUpdate"), fail_run("ls -la /made/up")))
    kit = stream_kit(str(tmp_path), [turn(bookkeeping(), bookkeeping(), fail_read("none.md"), fail_run("for f in a; do echo $f; done"), helper, hard_stop("spend"))], limits=(20.0, 14400.0))
    out = io.StringIO()
    got = LiveSession().attend(kit.harness, "do it", out, ScriptedKeys(), live=False, width=100)
    text = out.getvalue()
    assert got.final.outcome == "stopped" and "TaskCreate" not in text and "TaskUpdate" not in text
    assert text.count("Stopped at the spend limit") == 1 and "for f in" not in text and "ls -la" not in text and "Helper: Find one interesting finding" in text


def test_read_only_commands_are_allowed_by_rule_in_a_permission_mode_that_asks(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions import native_runner
    runner = native_runner.NativeToolLoopRunner(root=str(tmp_path), permission="acceptEdits")
    runner.local.settings_file = None
    runner.allow_read_only(str(tmp_path))
    rules = json.loads((tmp_path / "permission-rules.json").read_text())["permissions"]
    assert "Bash(find:*)" in rules["allow"] and "Bash(grep:*)" in rules["allow"] and "Bash(find:*-delete*)" in rules["deny"]
    assert not any(name in "".join(rules["allow"]) for name in ("Bash(rm", "Bash(sed", "Bash(awk", "Bash(git"))
    assert runner.local.settings_file == str(tmp_path / "permission-rules.json")
    free = native_runner.NativeToolLoopRunner(root=str(tmp_path), permission="skip")
    free.local.settings_file = None
    free.allow_read_only(str(tmp_path / "other"))
    assert free.local.settings_file is None                                           # no permission checks: nothing to allow


def test_the_harness_that_ran_a_session_is_recorded_so_resume_needs_no_flag(tmp_path):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_memory import SessionMemory, resolve_resume
    memory = SessionMemory(str(tmp_path / "work"), store=str(tmp_path / "state"))
    assert memory.last() is None and resolve_resume(memory, "last")[3] == "there is no earlier session in this folder to continue"
    assert memory.record("s1", "native", "fast") and memory.record("s2", "stream", "fast")
    assert resolve_resume(memory, "s1") == ("s1", "native", "", "")                      # the recorded harness is used when none is given
    assert resolve_resume(memory, "last") == ("s2", "stream", "", "")                    # the most recent session of this folder
    assert resolve_resume(memory, "s1", "native")[1:3] == ("native", "")
    said = resolve_resume(memory, "s1", "stream")                                        # an explicit flag wins, and a mismatch is said plainly
    assert said[1] == "stream" and "run by the native harness" in said[2] and "leave --harness out" in said[2]
    assert resolve_resume(memory, "never-recorded") == ("never-recorded", "", "", "")     # an unknown id is passed on; the default harness runs it
    other = SessionMemory(str(tmp_path / "elsewhere"), store=str(tmp_path / "state"))
    assert other.last() is None and other.find("s1")["harness"] == "native"              # `last` is per folder, an id is found anywhere
    assert SessionMemory(str(tmp_path), store="").record("s3", "native") is False


def test_the_closing_command_is_the_id_only_in_every_view():
    view = SessionView(command="ahohs work", session_id="abc", harness="native")
    assert present.resume_lines(view) == ["Continue this session later, in this folder:", "ahohs work --resume abc"]


def test_work_resumes_with_the_recorded_harness_and_last(tmp_path, monkeypatch, capsys):
    import argparse
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import work as terminal
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_memory import SessionMemory
    from hubofhubs.the_self.assembler import cli
    folder = tmp_path / "work"
    folder.mkdir()
    SessionMemory(str(folder), store=str(tmp_path / "state")).record("s7", "stream", "fast")
    seen = {}

    def fake_builder(**kwargs):
        seen["tier"] = kwargs["tier"]
        return lambda name: seen.setdefault("name", name) or None
    monkeypatch.setattr(terminal, "harness_builder", fake_builder)
    monkeypatch.setattr("hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_memory.SessionMemory.__init__",
                        lambda self, folder, store=None: (setattr(self, "folder", __import__("os").path.realpath(folder)), setattr(self, "path", str(tmp_path / "state" / "sessions.jsonl"))) and None)
    args = argparse.Namespace(folder=str(folder), max_spend=None, max_time=None, harness="", tier="fast", permission="acceptEdits", solution="", milestone="", setting_sources="project",
                              resume="last", goal="", plain=True, terminal="", records=None, person="", structure_watch="off", context="", focus="", task_kind="")
    seen["resume"] = None

    class Stop(Exception):
        pass

    def stop_at_terminal(*a, **k):
        raise Stop
    monkeypatch.setattr(terminal, "terminal_arm", stop_at_terminal)
    try:
        cli.work_command(args, object())
    except Stop:
        pass
    assert args.resume == "s7"                                                           # last became the recorded session's id
    args.resume = "nothing-here"
    args.harness = ""
    try:
        cli.work_command(args, object())
    except Stop:
        pass
    args.resume = "last"
    (tmp_path / "state" / "sessions.jsonl").unlink()
    assert cli.work_command(args, object()) == 2 and "no earlier session in this folder" in capsys.readouterr().err
