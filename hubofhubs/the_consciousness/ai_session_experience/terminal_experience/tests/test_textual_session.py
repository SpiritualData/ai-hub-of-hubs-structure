"""The Textual arm drawn headless on the scripted kits, the markdown text, the raw stream lines and the rough edges they fix: no model, no network."""
import io
import tempfile
from pathlib import Path

import pytest

from hubofhubs.the_consciousness.ai_session_experience.session_adapters import StreamJson, permission_refusal
from hubofhubs.the_consciousness.ai_session_experience.session_events import Step
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.markdown_text import markdown_lines
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import KITS, edit, read, report, turn
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import step_row


def test_markdown_is_styled_with_colour_and_untouched_without():
    text = "# Title\n\nThe **fast** path uses `cache`.\n\n- one\n- two\n\n```\nrun --now\n```"
    plain = markdown_lines(text, color=False)
    assert plain[0] == "# Title" and "**fast**" in "\n".join(plain)
    styled = "\n".join(markdown_lines(text, 60, color=True))
    assert "# Title" not in styled and "**" not in styled and "```" not in styled
    assert "• one" in styled and "run --now" in styled


def test_a_refused_tool_result_carries_its_reason_and_a_path_is_shown_inside_the_folder():
    stream = StreamJson("/work")
    use = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": "Bash", "input": {"command": "rm x"}}]}}
    stream.events(use)
    denied = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "is_error": True,
                                                       "content": "Claude requested permissions to use Bash, but you haven't granted it yet."}]}}
    row = [e for e in stream.events(denied) if isinstance(e, Step)][0]
    assert row.state == "blocked" and "permission" in row.detail and "refused:" in step_row(row)
    write = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "w", "name": "Write", "input": {"file_path": "/work/sub/a.txt"}}]}}
    assert stream.events(write)[0].label == "sub/a.txt" and list(stream.changed) == ["sub/a.txt"]
    assert permission_refusal({"content": "file not found"}) == "" and permission_refusal({"content": "bash: x: Permission denied"}) == ""
    real = "Output redirection to 'x.txt' needs approval. The path is inside the working directories, and Claude Code asks before a shell command creates files there."
    assert permission_refusal({"content": real}).startswith("Output redirection to 'x.txt' needs approval")


def test_a_helper_still_running_is_tracked():
    stream = StreamJson()
    stream.events({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a1", "name": "Task", "input": {"description": "check"}}]}})
    assert list(stream.open_agents) == ["a1"]
    stream.events({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a1", "content": "ok"}]}})
    assert not stream.open_agents


def test_the_textual_arm_runs_a_scripted_session_headless_and_leaves_the_transcript_on_out():
    pytest.importorskip("textual")
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.textual_session import TextualSession
    folder = tempfile.mkdtemp(prefix="tx-")
    Path(folder, "a.txt").write_text("alpha\n")
    kit = KITS["stream"](folder, [turn(read("a.txt")), turn(edit("b.txt")), turn(report("**All** done."))], pause=0.01)
    out = io.StringIO()
    rep = TextualSession().attend(kit.harness, "do it", out, ScriptedKeys(), tick=0.01, live=False, width=100)
    assert rep.final.outcome == "met" and "Changed (1): b.txt" in out.getvalue() and "ok read" in out.getvalue()
    assert "\x1b" not in out.getvalue()


def test_the_textual_arm_stops_and_resumes_like_the_reference_terminal():
    pytest.importorskip("textual")
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.textual_session import TextualSession
    keys = ScriptedKeys()
    folder = tempfile.mkdtemp(prefix="tx-")
    kit = KITS["stream"](folder, [turn(edit("one.txt")), turn(edit("two.txt"), hook=lambda: (keys.press("esc"), keys.press("line", "resume"))), turn(edit("three.txt"), report("All three."))], pause=0.01)
    rep = TextualSession().attend(kit.harness, "do it", io.StringIO(), keys, tick=0.01, live=False, width=100)
    assert rep.runs[0].outcome == "stopped" and rep.final.outcome == "met"


def test_without_textual_the_arm_is_unavailable_and_the_best_measured_arm_that_can_run_stands_in(monkeypatch):
    from hubofhubs.the_self.assembler import availability
    from hubofhubs.the_self.assembler.resolution import HUB
    assert availability.unmet(HUB, "terminal-session", "textual_session", {}, {}) == ""
    monkeypatch.setitem(__import__("sys").modules, "textual", None)
    why = availability.unmet(HUB, "terminal-session", "textual_session", {}, {})
    assert "textual" in why.lower(), why
    assert availability.unmet(HUB, "terminal-session", "live_session", {}, {}) == ""
