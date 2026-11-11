"""The hub's wrapper around an open-source harness (opencode here) run against a fake program: the frame reaches the harness as its own instructions, the code check and the
stop decision gate the hub's own continuation, the hard limit stops the process, and what the run touched outside the folder is reported."""
import json
import stat
import sys
import textwrap

import pytest

from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.framed_headless import OpencodeHubRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner import OpencodeRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings

FIRST = [{"type": "tool_use", "sessionID": "s1", "part": {"type": "tool", "tool": "bash", "state": {"status": "completed", "input": {"command": "sudo ls"}}}},
         {"type": "tool_use", "sessionID": "s1", "part": {"type": "tool", "tool": "write", "state": {"status": "completed", "input": {"filePath": "/srv/other/x.txt"}}}},
         {"type": "text", "sessionID": "s1", "part": {"type": "text", "text": "Report written."}},
         {"type": "step_finish", "sessionID": "s1", "part": {"type": "step-finish", "tokens": {"input": 100, "output": 10, "reasoning": 0}, "cost": 0.01}}]


def fake(tmp_path, *, writes_figure=True, sleep=0.0):
    """A program that records its calls, writes a report with an unsupported figure on its first call and a corrected one when its session is continued."""
    events = "\n".join(json.dumps(e) for e in FIRST)
    path = tmp_path / "fake_opencode"
    path.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import json, os, sys, time
        log = {str(tmp_path / 'calls.jsonl')!r}
        config = json.loads(os.environ.get("OPENCODE_CONFIG_CONTENT", "{{}}"))
        frame = [open(p).read() for p in config.get("instructions", [])]
        open(log, "a").write(json.dumps({{"argv": sys.argv[1:], "frame": frame}}) + "\\n")
        time.sleep({sleep})
        resumed = "--session" in sys.argv
        open(os.path.join({str(tmp_path / "work")!r}, "report.md"), "w").write("Revenue was 1.00 dollars.\\n" if resumed else "Revenue was 987654 dollars.\\n")
        print({events!r})
        """))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def build(tmp_path, program, **kwargs):
    (tmp_path / "work").mkdir(exist_ok=True)      # the folder the harness works in; the fake program and its log stay outside it
    config = SubprocessConfig(working_dir=str(tmp_path / "work"), claude_path=program, timeout_seconds=30.0)
    settings = GoalSettings(environment=lambda: {"PATH": "/usr/bin:/bin", "ANTHROPIC_API_KEY": "test"})
    return OpencodeHubRunner(config, provider="anthropic", tier="fast", settings=settings, model_for=lambda p, t: "tier-model", **kwargs)


def calls(tmp_path):
    return [json.loads(x) for x in (tmp_path / "calls.jsonl").read_text().splitlines()]


def test_the_frame_reaches_opencode_as_its_instructions_and_a_bare_arm_gets_none(tmp_path):
    (tmp_path / "work").mkdir(); (tmp_path / "work" / "notes.txt").write_text("the code is 4417\n")
    result = build(tmp_path, fake(tmp_path), check=False).run_goal(goal="report", brief="read notes.txt and report")
    assert result.met
    frame = calls(tmp_path)[0]["frame"][0]
    assert "FOLDER MAP" in frame and "notes.txt" in frame and "plan tool (todowrite)" in frame and "TaskCreate" not in frame
    bare = OpencodeRunner(SubprocessConfig(working_dir=str(tmp_path / "work"), claude_path=fake(tmp_path), timeout_seconds=30.0), provider="anthropic", tier="fast",
                          settings=GoalSettings(environment=lambda: {"PATH": "/usr/bin:/bin"}), model_for=lambda p, t: "m")
    bare.run_goal(goal="report", brief="report")
    assert calls(tmp_path)[-1]["frame"] == []


def test_the_outside_folder_report_and_session_events(tmp_path):
    events = []
    result = build(tmp_path, fake(tmp_path), check=False).run_goal(goal="g", brief="g", emit=events.append)
    assert any("sudo" in line for line in result.outside_folder) and any("/srv/other/x.txt" in line for line in result.outside_folder)
    sessions = [e.data for e in events if e.type == "session"]
    assert sessions[0]["type"] == "run-started" and [s["kind"] for s in sessions if s["type"] == "step"].count("bash") >= 1 and sessions[-1]["type"] == "usage"


def test_the_code_check_continues_the_session_only_when_the_stop_decision_allows_it(tmp_path):
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "source.txt").write_text("Revenue figures: 1.00 dollars in total.\n")
    asked = []
    allow = lambda facts: asked.append(list(facts["findings"])) or {"continue": True, "reason": "code_finding"}
    result = build(tmp_path, fake(tmp_path), should_continue=allow).run_goal(goal="g", brief="g")
    assert len(asked) >= 1 and len(calls(tmp_path)) == 2 and "--session" in calls(tmp_path)[1]["argv"] and "987654" in " ".join(calls(tmp_path)[1]["argv"])
    assert (tmp_path / "work" / "report.md").read_text() == "Revenue was 1.00 dollars.\n" and result.cost_usd > 0.01 - 1e-9
    (tmp_path / "calls.jsonl").unlink()
    refused = build(tmp_path, fake(tmp_path), should_continue=lambda facts: {"continue": False, "reason": "ceiling_spend"}).run_goal(goal="g", brief="g")
    assert len(calls(tmp_path)) == 1 and refused.end_reason == "resume_stopped:ceiling_spend" and refused.met


def test_the_hard_limit_stops_the_process_and_keeps_the_session_to_resume(tmp_path):
    result = build(tmp_path, fake(tmp_path, sleep=30.0), ceiling_seconds=1.5, ceiling_usd=5.0, check=False).run_goal(goal="g", brief="g")
    assert not result.met and result.cancelled and "hard limit" in result.error


def test_the_hubs_continuation_adds_the_resumed_invocations_own_steps_to_the_account(tmp_path):
    # opencode records cost and tokens per step and a resumed invocation prints only its own new steps (checked in opencode's stored sessions: step costs are not
    # running totals), so the account of a run with one continuation is the sum of the two invocations, unlike a Claude Code session whose reported cost is cumulative.
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "source.txt").write_text("Revenue figures: 1.00 dollars in total.\n")
    allow = lambda facts: {"continue": True, "reason": "code_finding"}
    result = build(tmp_path, fake(tmp_path), should_continue=allow).run_goal(goal="g", brief="g")
    assert len(calls(tmp_path)) == 2 and result.cost_usd == pytest.approx(0.02) and result.tokens == 220
