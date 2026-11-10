"""The hub's frame on the model's own tool loop (``native_runner``): offline, the ``claude`` program is a fake script that speaks stream-json.

It records its argv and its first message, writes a file when told to, and ends with a result event the way the real CLI does."""
import json
import os
import stat
import sys

import pytest

from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS, RULES, build_frame
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings, lean_flags
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import NativeToolLoopRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings

FAKE = '''#!{python}
import json, os, sys
log = os.environ["FAKE_LOG"]
args = sys.argv[1:]
if args == ["--version"]:
    print("2.1.400 (Claude Code)"); sys.exit(0)
turn = 0
with open(log, "a") as out:
    out.write(json.dumps({{"argv": args, "tmpdir": os.environ.get("TMPDIR", ""), "cwd": os.getcwd()}}) + "\\n")
for line in sys.stdin:
    message = json.loads(line)
    if message.get("type") != "user":
        continue
    text = message["message"]["content"]
    turn += 1
    with open(log, "a") as out:
        out.write(json.dumps({{"message": text}}) + "\\n")
    print(json.dumps({{"type": "system", "subtype": "init", "session_id": "sess-1"}}), flush=True)
    print(json.dumps({{"type": "user", "message": {{"role": "user", "content": text}}}}), flush=True)
    if "write the report" in text:
        open("report.md", "w").write("The total is 4242 units.")
    reply = "done: figures fixed" if "code check" in text else "report written"
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "result": reply, "session_id": "sess-1",
                      "total_cost_usd": 0.01, "usage": {{"input_tokens": 100, "output_tokens": 20}}}}), flush=True)
    break
'''


def fake_claude(tmp_path):
    path = tmp_path / "claude"
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def runner_for(tmp_path, monkeypatch, **kwargs):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    (work / "notes.txt").write_text("the limit is 100\n")
    log = tmp_path / "log.jsonl"
    monkeypatch.setenv("FAKE_LOG", str(log))
    env = {"PATH": "/usr/bin:/bin", "FAKE_LOG": str(log)}
    cfg = SubprocessConfig(working_dir=str(work), claude_path=fake_claude(tmp_path), review_interval_seconds=0, timeout_seconds=60)
    runner = NativeToolLoopRunner(cfg, settings=GoalSettings(environment=lambda: dict(env)), provider="anthropic", tier="fast",
                                  session_dir=str(tmp_path / "sessions"), **kwargs)
    return runner, log, work


def records(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_the_session_is_lean_framed_and_in_the_working_folder(tmp_path, monkeypatch):
    runner, log, work = runner_for(tmp_path, monkeypatch)
    got = runner.run_goal(goal="read the notes", brief="read the notes and report the limit", max_turns=5)
    assert got.met and got.output == "report written" and got.session_id
    launch = records(log)[0]
    argv = launch["argv"]
    assert argv[argv.index("--tools") + 1] == ",".join(NATIVE_TOOLS)
    assert "WebSearch" in NATIVE_TOOLS and "WebFetch" in NATIVE_TOOLS and "Bash" in NATIVE_TOOLS
    assert argv[argv.index("--setting-sources") + 1] == "" and "--strict-mcp-config" in argv and "--dangerously-skip-permissions" in argv
    frame_path = argv[argv.index("--append-system-prompt-file") + 1]
    frame = open(frame_path, encoding="utf-8").read()
    assert RULES in frame and "notes.txt" in frame and "the limit is 100" in frame     # the rules, the folder map and the file in view
    assert launch["tmpdir"] and launch["tmpdir"].startswith(str(tmp_path / "sessions"))   # the session's private temporary folder
    assert os.path.realpath(launch["cwd"]) == os.path.realpath(str(work))


def test_tokens_and_cost_are_the_siblings_basis(tmp_path, monkeypatch):
    runner, _log, _work = runner_for(tmp_path, monkeypatch)
    got = runner.run_goal(goal="g", brief="b")
    assert got.tokens == 120 and got.cost_usd == pytest.approx(0.01)


def test_a_figure_no_source_holds_resumes_the_same_session_once_with_the_finding(tmp_path, monkeypatch):
    runner, log, work = runner_for(tmp_path, monkeypatch)
    got = runner.run_goal(goal="write the report", brief="write the report on the notes")
    launches = [r for r in records(log) if "argv" in r]
    messages = [r["message"] for r in records(log) if "message" in r]
    assert len(launches) == 2 and launches[1]["argv"][launches[1]["argv"].index("--resume") + 1] == launches[0]["argv"][launches[0]["argv"].index("--session-id") + 1]
    assert "4242" in messages[1] and "code check" in messages[1]
    assert got.met and got.output == "done: figures fixed" and got.tokens == 240 and got.cost_usd == pytest.approx(0.02)


def test_the_code_check_can_be_turned_off(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, check=False)
    got = runner.run_goal(goal="write the report", brief="write the report on the notes")
    assert got.met and len([r for r in records(log) if "argv" in r]) == 1


def test_the_frame_is_pure_and_survives_a_folder_it_cannot_read(tmp_path):
    (tmp_path / "a.txt").write_text("alpha\n")
    frame = build_frame("report on a.txt", "", str(tmp_path))
    assert "a.txt" in frame.text and frame.shown == ["a.txt"]
    def broken(*a, **k):
        raise RuntimeError("no selection")
    assert build_frame("g", "", str(tmp_path), select=broken).text == RULES


def test_the_new_launch_parameter_adds_only_its_flag():
    assert lean_flags(DeepLaunchSettings()) == []
    assert lean_flags(DeepLaunchSettings(append_system_prompt_file="/x/f.md")) == ["--append-system-prompt-file", "/x/f.md"]


def test_the_arm_is_declared_on_trial_and_paid():
    assert NativeToolLoopRunner.on_trial is True and NativeToolLoopRunner.PAID is True and NativeToolLoopRunner.PROVIDERS == ("anthropic",)
