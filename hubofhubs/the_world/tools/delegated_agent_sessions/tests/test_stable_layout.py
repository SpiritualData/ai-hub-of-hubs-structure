"""The layout that keeps a long run cheap: everything that does not change lives in the system text; the message holds only what changed. And a stray reply
does not end a run. Scripted completion, no model."""
import logging
from pathlib import Path

import pytest

from hubofhubs.the_world.model_plumbing.vendor_model_caller import claude_cli
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import LoopState, run_loop
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner


class Script:
    def __init__(self, *replies, repeat=None):
        self.replies, self.systems, self.prompts, self.repeat = list(replies), [], [], repeat

    def __call__(self, system, prompt):
        self.systems.append(system)
        self.prompts.append(prompt)
        if self.replies:
            return self.replies.pop(0)
        return self.repeat or "BLOCKED: script ended"


def write(root, name, text):
    path = Path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def message_of(script, index):
    return script.prompts[index]


# --- 1. the shape of the real run -----------------------------------------------------------------------------------------------------

def test_a_long_goal_a_long_context_and_twenty_named_files_leave_a_small_message_and_one_system_text(tmp_path):
    names = [f"ref/file{n:02d}.txt" for n in range(20)]
    for name in names:
        write(tmp_path, name, f"{name} " + "reference text. " * 500)
    goal = "Weekly run\n" + "Do the step and record it. " * 1000
    context = "Reference files this work uses: " + ", ".join(names) + ". " + "Standing rule. " * 3300
    script = Script(*[f"RUN: echo step{n}\nNOTE: step {n}\n" for n in range(1, 6)], "RUN: echo last\nREPORT: done\n")
    got = run_loop(goal, working_dir=str(tmp_path), complete=script, context=context, max_calls=8, review=False)
    assert got.met and got.calls == 6 and len(goal) > 26_000 and len(context) > 46_000
    assert len({s for s in script.systems}) == 1                                    # the system text is the same at every call
    assert all(len(prompt) < 20_000 for prompt in script.prompts)                   # and the message is small at every call, the first included
    system = script.systems[0]
    assert goal.strip() in system and context.strip() in system and "FOLDER MAP AT THE START" in system
    assert system.count("=== ref/") <= 12                                           # the view is bounded by view_chars, not by what the context names
    assert "[not in view: READ it before relying on it]" in system                  # what did not fit is listed in the map as a file to read


def test_the_message_holds_only_what_changed_and_the_stable_content_is_never_in_it(tmp_path):
    write(tmp_path, "notes.txt", "keep this " * 600)
    goal = "Make the report\n" + "detail. " * 1200
    script = Script("RUN: echo made > new.txt\nNOTE: made", "REPORT: ok\n")
    run_loop(goal, working_dir=str(tmp_path), complete=script, context="Standing rules. " * 800, review=False)
    first, second = message_of(script, 0), message_of(script, 1)
    for message in (first, second):
        assert "detail. detail." not in message and "Standing rules." not in message and "FOLDER MAP" not in message and "keep this keep this" not in message
        assert message.startswith("GOAL:\nMake the report (the full goal is in your instructions)")
    assert "NEW FILES IN THE FOLDER SINCE THE START" in second and "new.txt" in second and "NEW FILES" not in first
    assert script.systems[0] == script.systems[1]


def test_a_small_run_keeps_everything_in_the_message_as_before(tmp_path):
    write(tmp_path, "a.txt", "alpha\n")
    script = Script("It is alpha.")
    run_loop("What is in a.txt?", working_dir=str(tmp_path), complete=script, context="Be brief.", cache_chars=50_000)
    assert "CONTEXT:\nBe brief." in script.prompts[0] and "FOLDER MAP" in script.prompts[0]


def test_over_the_system_budget_files_leave_the_view_but_the_goal_and_context_stay_whole(tmp_path):
    for n in range(6):
        write(tmp_path, f"f{n}.txt", f"f{n} " + "x" * 9_000)
    goal = "Use f0.txt f1.txt f2.txt f3.txt f4.txt f5.txt\n" + "goal words. " * 900
    context = "context words. " * 900
    script = Script("Fine.")
    run_loop(goal, working_dir=str(tmp_path), complete=script, context=context, system_chars=40_000, review=False)
    system = script.systems[0]
    assert goal.strip() in system and context.strip() in system and system.count("=== f") < 6
    assert "f5.txt" in system.split("FOLDER MAP AT THE START")[1] and "not in view" in system
    assert len(script.prompts[0]) < 8_000


def test_the_view_is_one_budget_goal_named_files_first_context_only_files_last(tmp_path):
    write(tmp_path, "goal_named.txt", "G" * 30_000)
    write(tmp_path, "context_only.txt", "C" * 30_000)
    write(tmp_path, "other.txt", "O" * 20_000)
    script = Script("Fine.")
    run_loop("Work from goal_named.txt", working_dir=str(tmp_path), complete=script, context="Background lives in context_only.txt", view_chars=50_000, review=False)
    system = script.systems[0]
    assert "G" * 1000 in system and "C" * 1000 not in system
    assert "context_only.txt (30000 bytes)  [not in view: READ it before relying on it]" in system


# --- 2. a stray reply does not end the run ----------------------------------------------------------------------------------------------

def test_a_reply_with_no_action_is_nudged_every_time_it_follows_a_reply_that_acted(tmp_path):
    script = Script("RUN: echo one\nNOTE: one", "I will continue now", "RUN: echo two\nNOTE: two", "Still thinking", "RUN: echo three\nREPORT: all three ran\n")
    got = run_loop("Three steps", working_dir=str(tmp_path), complete=script, review=False)
    assert got.met and got.report == "all three ran" and got.commands == 3
    assert "none of the actions" in script.prompts[2] and "none of the actions" in script.prompts[4]


def test_two_replies_in_a_row_without_an_action_end_the_run_not_met_with_the_work_so_far_and_a_resumable_session(tmp_path):
    saved = []
    script = Script("RUN: echo one > made.txt\nNOTE: made the file", "hm", "hmm")
    got = run_loop("Make it", working_dir=str(tmp_path), complete=script, review=False, save=saved.append)
    assert not got.met and "twice in a row" in got.error and got.report == "made the file" and got.commands == 1
    assert (tmp_path / "made.txt").exists() and saved and isinstance(saved[-1], LoopState) and saved[-1].calls == 3


def test_long_prose_with_no_action_after_work_is_taken_as_the_report_and_a_short_one_is_not(tmp_path):
    answer = "I made made.txt and checked it exists. " * 12
    script = Script("RUN: echo one > made.txt\nNOTE: made", answer)
    got = run_loop("Make it", working_dir=str(tmp_path), complete=script, review=False)
    assert got.met and got.report == answer.strip()
    script = Script("RUN: echo one > made.txt\nNOTE: made", "Done.", "Done.")
    assert not run_loop("Make it", working_dir=str(tmp_path / "x") if (tmp_path / "x").mkdir() is None else str(tmp_path), complete=script, review=False).met
    script = Script("RUN: echo one\nNOTE: made", ("Which one do you want? " * 20).strip() + "?", "x")
    assert not run_loop("Make it", working_dir=str(tmp_path), complete=script, review=False).met


# --- 3. cache visibility ------------------------------------------------------------------------------------------------------------------

class Provider:
    def __init__(self, **ignored):
        self.tokens_in = self.tokens_out = self.cache_read_tokens = self.cache_creation_tokens = 0
        self.cost_usd = 0.0
        self.calls = 0

    def answer(self, messages, *, model, system=None):
        self.calls += 1
        first = self.calls == 1
        self.tokens_in += 2 + (0 if first else 30_000) + (80_000 if first else 1_000)
        self.cache_read_tokens += 0 if first else 30_000
        self.cache_creation_tokens += 80_000 if first else 1_000
        self.tokens_out += 100
        self.cost_usd += 0.01
        return "RUN: echo hi\nNOTE: n\n" if self.calls < 3 else "REPORT: done\n"


def test_usage_carries_cache_read_and_write_and_the_run_ends_with_one_totals_line(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(claude_cli, "ClaudeCliProvider", Provider)
    runner = SolutionLoopRunner(root=str(tmp_path), model_for=lambda provider, tier: "m", sandbox=False, review=False, session_dir=str(tmp_path / "s"))
    seen = []
    with caplog.at_level(logging.INFO, logger="hubofhubs.deep"):
        runner.work("Do it", emit=seen.append)
    usage = [e.data for e in seen if e.type == "session" and e.data["type"] == "usage"]
    assert [u["cache_write_tokens"] for u in usage][0] == 80_000 and usage[-1]["cache_read_tokens"] == 60_000 and usage[-1]["cache_write_tokens"] == 82_000
    totals = [r.getMessage() for r in caplog.records if "totals" in r.getMessage()]
    assert totals == ["loop run totals: 3 calls, plain input 6, cache read 60000, cache write 82000, output 300, cost $0.0300, ended: met"]
    assert any("plain input 2, cache read 0, cache write 80000, output 100" in r.getMessage() for r in caplog.records)


def test_a_system_text_longer_than_one_argument_goes_through_a_private_file_that_is_removed(tmp_path, monkeypatch):
    captured = {}

    def fake_run(cmd, *, input, env, cwd, timeout):
        index = cmd.index("--system-prompt-file")
        path = cmd[index + 1]
        captured["text"] = Path(path).read_text(encoding="utf-8")
        captured["mode"] = Path(path).stat().st_mode & 0o777
        captured["path"] = path
        import subprocess
        return subprocess.CompletedProcess(cmd, 0, b'{"result": "OK", "usage": {}}', b"")
    monkeypatch.setattr(claude_cli, "run_in_group", fake_run)
    monkeypatch.setattr(claude_cli, "_supported_flags", lambda binary: frozenset({"--exclude-dynamic-system-prompt-sections", "--system-prompt-file"}))
    provider = claude_cli.ClaudeCliProvider(claude_path="claude")
    monkeypatch.setattr(provider, "_resolve_binary", lambda: "claude")
    system = "S" * 200_000
    assert provider.answer([{"role": "user", "content": "hi"}], model="m", system=system) == "OK"
    assert captured["text"] == system and captured["mode"] == 0o600 and not Path(captured["path"]).exists()
