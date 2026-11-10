"""Four defects a real multi-step task found in the hub loop: token accounting, a /tmp that did not last, commands of several lines, and a message
that carried the whole brief at every call. Scripted completion and a fake provider: no model."""
import logging
import os
import shutil
import stat

import pytest

from hubofhubs.the_world.model_plumbing.vendor_model_caller import claude_cli
from hubofhubs.the_world.tools.command_running import run_command, sandbox_wrap
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import HISTORY_CHARS, Outcome, history_text, parse_reply, run_loop
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner

needs_bwrap = pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not installed")
FENCE = "`" * 3


class Script:
    def __init__(self, *replies):
        self.replies, self.systems, self.prompts = list(replies), [], []

    def __call__(self, system, prompt):
        self.systems.append(system)
        self.prompts.append(prompt)
        return self.replies.pop(0) if self.replies else "BLOCKED: script ended"


# --- 1. tokens on the sibling runner's basis ---------------------------------------------------------------------------------------------

class CachingProvider:
    """A provider whose input count includes cache reads and writes, as the Claude CLI provider's does."""

    def __init__(self, **ignored):
        self.tokens_in = self.tokens_out = self.cache_read_tokens = self.cache_creation_tokens = 0
        self.cost_usd = 0.0

    def answer(self, messages, *, model, system=None):
        self.tokens_in += 500 + 100_000 + 3_000
        self.cache_read_tokens += 100_000
        self.cache_creation_tokens += 3_000
        self.tokens_out += 50
        self.cost_usd += 0.01
        return "It is a."


def test_tokens_are_plain_input_plus_output_whatever_the_cache_read(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(claude_cli, "ClaudeCliProvider", CachingProvider)
    (tmp_path / "a.txt").write_text("a\n")
    runner = SolutionLoopRunner(root=str(tmp_path), model_for=lambda provider, tier: "m", sandbox=False, review=False, session_dir=str(tmp_path / "s"))
    seen = []
    with caplog.at_level(logging.INFO, logger="hubofhubs.deep"):
        result, usage, _why = runner.work("What is in a.txt?", emit=seen.append)
    assert usage["tokens"] == 550 and usage["cost"] == pytest.approx(0.01)
    assert any(e.type == "session" and e.data["type"] == "usage" and e.data["tokens"] == 550 for e in seen)
    assert any("plain input 500, cache read 100000, cache write 3000, output 50" in r.getMessage() for r in caplog.records)


# --- 2. a /tmp that lasts the whole run ----------------------------------------------------------------------------------------------------

@needs_bwrap
def test_a_file_written_to_tmp_is_read_by_the_next_command_and_the_rest_stays_read_only(tmp_path):
    work, scratch = tmp_path / "work", tmp_path / "scratch"
    work.mkdir()
    scratch.mkdir()
    wrap = sandbox_wrap(str(work), scratch=str(scratch))
    assert run_command("echo kept > /tmp/step1.txt", working_dir=str(work), wrap=wrap).code == 0
    read = run_command("cat /tmp/step1.txt; echo $TMPDIR", working_dir=str(work), wrap=wrap)
    assert read.code == 0 and read.output.split() == ["kept", "/tmp"]
    assert (scratch / "step1.txt").exists()
    assert run_command("echo no > /etc/nope.txt", working_dir=str(work), wrap=wrap).code != 0
    assert run_command("mkdir -p ~/.cache/x", working_dir=str(work), wrap=wrap).code != 0
    assert run_command("mkdir -p $XDG_CACHE_HOME/x && echo ok", working_dir=str(work), wrap=wrap).output.strip() == "ok"


@needs_bwrap
def test_without_a_scratch_folder_each_command_still_gets_an_empty_tmp(tmp_path):
    wrap = sandbox_wrap(str(tmp_path))
    run_command("echo a > /tmp/once.txt", working_dir=str(tmp_path), wrap=wrap)
    assert run_command("test -e /tmp/once.txt", working_dir=str(tmp_path), wrap=wrap).code != 0


def test_the_runner_keeps_one_private_scratch_folder_per_session_and_a_resume_finds_it(tmp_path):
    runner = SolutionLoopRunner(root=str(tmp_path), complete=Script("ok"), session_dir=str(tmp_path / "s"))
    first = runner.scratch_folder("session-1")
    assert first == runner.scratch_folder("session-1") != runner.scratch_folder("session-2")
    assert stat.S_IMODE(os.stat(first).st_mode) == 0o700 and first.startswith(str(tmp_path / "s"))


def test_the_system_text_says_where_commands_can_write_when_a_sandbox_is_on(tmp_path):
    script = Script("It is a.")
    run_loop("What?", working_dir=str(tmp_path), complete=script, wrap=("env",))
    assert "kept for the whole run" in script.systems[0] and "everything else is read-only" in script.systems[0]
    plain = Script("It is a.")
    run_loop("What?", working_dir=str(tmp_path), complete=plain)
    assert "kept for the whole run" not in plain.systems[0]


# --- 3. commands of several lines ---------------------------------------------------------------------------------------------------------

def test_a_heredoc_after_run_is_one_command_with_its_body():
    reply = parse_reply("NOTE: go\nRUN: python3 - <<'EOF'\nprint(1)\nprint(2)\nEOF\nRUN: echo after\nREPORT: done\n")
    commands = [a.text for a in reply.actions if a.kind == "run"]
    assert commands == ["python3 - <<'EOF'\nprint(1)\nprint(2)\nEOF", "echo after"]


def test_a_fenced_shell_block_is_one_command_and_a_fence_inside_a_report_is_not_run():
    text = f"Plan:\n{FENCE}bash\nset -e\ncd sub\nls\n{FENCE}\nREPORT: I ran this:\n{FENCE}bash\nrm -rf data\n{FENCE}\n"
    reply = parse_reply(text)
    assert [a.text for a in reply.actions if a.kind == "run"] == ["set -e\ncd sub\nls"]
    assert "rm -rf data" in (reply.report or "")


def test_a_fenced_block_inside_an_edit_block_is_file_text_and_a_plain_fence_is_not_a_command():
    edit = f"notes.md\n{'<' * 7} SEARCH\n{'=' * 7}\n{FENCE}bash\nls\n{FENCE}\n{'>' * 7} REPLACE\n{FENCE}\nnot a command\n{FENCE}\n"
    reply = parse_reply(edit)
    assert [a.kind for a in reply.actions] == ["edit"]


def test_a_multi_line_command_runs_and_uses_the_file_an_earlier_one_wrote(tmp_path):
    reply = f"{FENCE}bash\nprintf 'a\\nb\\n' > made.txt\nwc -l < made.txt\n{FENCE}\nRUN: python3 - <<'EOF'\nprint(open('made.txt').read().count('a'))\nEOF\nREPORT: ok\n"
    got = run_loop("Work", working_dir=str(tmp_path), complete=Script(reply))
    assert got.met and got.commands == 2 and (tmp_path / "made.txt").read_text() == "a\nb\n"


# --- 4. a long goal is kept in the system text, the history is bounded, the sizes are logged ------------------------------------

def test_a_long_goal_is_in_the_system_text_and_the_message_names_it_by_its_first_line(tmp_path, caplog):
    brief = "Weekly run\n" + "step detail. " * 3000
    script = Script("It is done.")
    with caplog.at_level(logging.INFO, logger="hubofhubs.deep"):
        run_loop(brief, working_dir=str(tmp_path), complete=script)
    assert "step detail. " * 100 in script.systems[0] and "step detail" not in script.prompts[0]
    assert script.prompts[0].startswith("GOAL:\nWeekly run (the full goal is in your instructions)")
    line = next(r.getMessage() for r in caplog.records if "call 1: system" in r.getMessage())
    assert "message" in line and "history" in line


def test_a_short_goal_stays_in_the_message(tmp_path):
    script = Script("Fine.")
    run_loop("Say fine", working_dir=str(tmp_path), complete=script)
    assert "GOAL:\nSay fine" in script.prompts[0] and "GOAL (the full text" not in script.systems[0]


def test_the_history_shrinks_older_calls_past_its_budget_and_keeps_the_latest_whole():
    big = "x" * 5000
    entries = [{"call": n, "note": "", "advice": "", "outcomes": [Outcome("RUN a", True, big)]} for n in range(1, 30)]
    text = history_text(entries)
    assert len(text) < HISTORY_CHARS + 6000 and big in text.split("Call 29:")[1]
    assert len(history_text(entries[:3])) > 3 * 280


def test_a_multi_line_command_is_named_by_its_first_line_in_its_step(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import Telling
    got = []
    reply = f"{FENCE}bash\nmkdir -p r\necho a > r/a.txt\n{FENCE}\nREPORT: ok\n"
    run_loop("Work", working_dir=str(tmp_path), complete=Script(reply), telling=Telling(got.append))
    labels = [e["label"] for e in got if e["type"] == "step" and e["kind"] == "run"]
    assert labels and all(label == "mkdir -p r (+1 more lines)" for label in labels)
