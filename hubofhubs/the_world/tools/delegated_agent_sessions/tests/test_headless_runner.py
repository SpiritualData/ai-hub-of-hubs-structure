"""The offline stage of the harness arms: Codex CLI and opencode run against a fake program that replays each harness's recorded event
stream, so the runner contract (report, tokens, cost, launch failure, time limit, cancel, escalation, credentials) is checked with no model."""
import json
import os
import stat
import sys
import textwrap

import pytest

from hubofhubs.the_world.tools.delegated_agent_sessions import providers
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner import CodexCliRunner, OpencodeRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings
from hubofhubs.the_world.tools.delegated_agent_sessions.subprocess_runner import SubprocessGoalRunner

CODEX_EVENTS = [
    {"type": "thread.started", "thread_id": "thread-1"},
    {"type": "item.completed", "item": {"id": "i0", "type": "reasoning", "text": "thinking"}},
    {"type": "item.completed", "item": {"id": "i1", "type": "agent_message", "text": "The meeting is in Rotterdam."}},
    {"type": "turn.completed", "usage": {"input_tokens": 1200, "cached_input_tokens": 0, "output_tokens": 40}},
]

OPENCODE_EVENTS = [
    {"type": "step_start", "sessionID": "ses_1", "part": {"type": "step-start"}},
    {"type": "tool_use", "sessionID": "ses_1", "part": {"type": "tool", "tool": "read", "state": {"status": "completed"}}},
    {"type": "step_finish", "sessionID": "ses_1", "part": {"type": "step-finish", "tokens": {"input": 900, "output": 10, "reasoning": 0}, "cost": 0.001}},
    {"type": "text", "sessionID": "ses_1", "part": {"type": "text", "text": "The meeting is in Rotterdam."}},
    {"type": "step_finish", "sessionID": "ses_1", "part": {"type": "step-finish", "tokens": {"input": 950, "output": 12, "reasoning": 0}, "cost": 0.002}},
]


def fake_program(tmp_path, events, *, exit_code=0, sleep=0.0, stderr="", echo_env=""):
    """A program that records its arguments, stdin and one environment variable, then prints ``events`` as JSON lines."""
    lines = "\n".join(json.dumps(e) for e in events)
    script = tmp_path / "fake_harness"
    script.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import json, os, sys, time
        record = {{"argv": sys.argv[1:], "stdin": sys.stdin.read(), "env": os.environ.get({echo_env!r}, "")}}
        open({str(tmp_path / 'call.json')!r}, "w").write(json.dumps(record))
        time.sleep({sleep})
        print({lines!r})
        sys.stderr.write({stderr!r})
        sys.exit({exit_code})
        """))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def call(tmp_path):
    return json.loads((tmp_path / "call.json").read_text())


def build(cls, tmp_path, program, *, provider, env=None, timeout=30.0, marker=""):
    config = SubprocessConfig(working_dir=str(tmp_path), claude_path=program, timeout_seconds=timeout)
    environment = dict(env or {}, PATH="/usr/bin:/bin")
    settings = GoalSettings(environment=lambda: dict(environment), escalation_marker=marker)
    return cls(config, provider=provider, tier="fast", settings=settings, model_for=lambda p, t: f"{p}-{t}-model")


def test_codex_report_tokens_and_list_price(tmp_path, monkeypatch):
    runner = build(CodexCliRunner, tmp_path, fake_program(tmp_path, CODEX_EVENTS), provider="openai")
    monkeypatch.setattr("hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner.list_price", lambda p, m, i, o: 0.5)
    res = runner.run_goal(goal="name the city", brief="read notes.txt")
    assert res.met and res.output == "The meeting is in Rotterdam."
    assert res.tokens == 1240 and res.cost_usd == 0.5 and res.session_id == "thread-1"
    got = call(tmp_path)
    assert got["argv"][:2] == ["exec", "--json"] and got["argv"][-1] == "-" and "openai-fast-model" in got["argv"]
    assert "read notes.txt" in got["stdin"] and str(tmp_path) in got["stdin"]   # the prompt goes on stdin and names the folder


def test_opencode_report_cost_and_provider_mapping(tmp_path):
    program = fake_program(tmp_path, OPENCODE_EVENTS, echo_env="GOOGLE_GENERATIVE_AI_API_KEY")
    runner = build(OpencodeRunner, tmp_path, program, provider="gemini", env={"GEMINI_API_KEY": "test-key"})
    res = runner.run_goal(goal="name the city", brief="read notes.txt", model="claude-sonnet")
    assert res.met and "Rotterdam" in res.output
    assert res.tokens == 1872 and res.cost_usd == pytest.approx(0.003)
    got = call(tmp_path)
    assert "google/gemini-fast-model" in got["argv"]   # the arm's own model: a Claude ladder model is not used on another provider
    assert got["env"] == "test-key"                      # opencode's Google SDK reads its own variable name
    assert not runner.uses_deep_model


def test_launch_failure_is_not_a_failed_goal(tmp_path):
    error = [{"type": "error", "error": {"name": "ProviderAuthError", "data": {"message": "no key"}}}]
    runner = build(OpencodeRunner, tmp_path, fake_program(tmp_path, error, exit_code=1), provider="gemini")
    res = runner.run_goal(goal="g", brief="b")
    assert not res.met and res.launch_failed and "no key" in res.error


def test_missing_program(tmp_path):
    runner = build(CodexCliRunner, tmp_path, str(tmp_path / "absent"), provider="openai")
    res = runner.run_goal(goal="g", brief="b")
    assert not res.met and res.launch_failed and res.launch_problem == "missing_program"


def test_time_limit_stops_the_run(tmp_path):
    runner = build(CodexCliRunner, tmp_path, fake_program(tmp_path, CODEX_EVENTS, sleep=30), provider="openai", timeout=1.5)
    res = runner.run_goal(goal="g", brief="b")
    assert not res.met and "time limit" in res.error


def test_cancel_stops_the_run(tmp_path):
    runner = build(CodexCliRunner, tmp_path, fake_program(tmp_path, CODEX_EVENTS, sleep=30), provider="openai")
    res = runner.run_goal(goal="g", brief="b", cancel_check=lambda: True)
    assert not res.met and res.cancelled


def test_escalation_marker_hands_back_the_decision(tmp_path):
    events = [{"type": "item.completed", "item": {"type": "agent_message", "text": "Raised it.\nASK-HUMAN: dec_abc123"}},
              {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}}]
    runner = build(CodexCliRunner, tmp_path, fake_program(tmp_path, events), provider="openai", marker="ASK-HUMAN:")
    res = runner.run_goal(goal="g", brief="b")
    assert not res.met and res.decision_id == "dec_abc123"


def test_ended_without_a_message_is_not_met(tmp_path):
    events = [{"type": "step_finish", "part": {"tokens": {"input": 100, "output": 1}, "cost": 0.0001}}]
    runner = build(OpencodeRunner, tmp_path, fake_program(tmp_path, events), provider="gemini")
    res = runner.run_goal(goal="g", brief="b")
    assert not res.met and "without a final message" in res.error


def test_providers_are_declared_per_harness(tmp_path):
    assert providers.drives(SubprocessGoalRunner, "anthropic") and not providers.drives(SubprocessGoalRunner, "gemini")
    assert providers.drives(CodexCliRunner, "openai") and not providers.drives(CodexCliRunner, "gemini")
    assert all(providers.drives(OpencodeRunner, p) for p in ("anthropic", "openai", "google", "deepseek"))
    with pytest.raises(ValueError):
        CodexCliRunner(SubprocessConfig(working_dir=str(tmp_path)), provider="gemini", model_for=lambda p, t: "m")
    with pytest.raises(ValueError):
        SubprocessGoalRunner(SubprocessConfig(working_dir=str(tmp_path)), provider="openai")
