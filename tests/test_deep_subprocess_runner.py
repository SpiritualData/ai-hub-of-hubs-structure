"""The subprocess goal runner (``hubofhubs.deep.subprocess_runner``) with every setting handed in: offline, the process is a fake.

What a consumer supplies (the escalation marker, a usage-limit state, the name of the run-id variable, a requester hook, the
environment a child starts from, the sessions directory) is passed as ``GoalSettings`` and observed at the process edge.
"""
from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

from hubofhubs.deep.settings import GoalSettings, UsageLimits
from hubofhubs.deep.subprocess_runner import SubprocessGoalRunner
from hubofhubs.deep.contract import SubprocessConfig

MARKER = "WORKER-ESCALATED:"


def envelope(text, *, is_error=False, usage=None, subtype="success"):
    return json.dumps({"result": text, "is_error": is_error, "subtype": subtype, "total_cost_usd": 0.25,
                       "usage": usage if usage is not None else {"input_tokens": 10, "output_tokens": 5}})


class FakePopen:
    seen = []

    def __init__(self, cmd, **kwargs):
        self.cmd, self.kwargs, self.returncode = cmd, kwargs, FakePopen.reply[0]
        self.pid = 4242
        FakePopen.seen.append(self)

    def communicate(self, input=None, timeout=None):
        self.stdin_text = (input or b"").decode()
        return FakePopen.reply[1].encode(), FakePopen.reply[2].encode()


def run(monkeypatch, reply, settings=None, **cfg):
    FakePopen.seen, FakePopen.reply = [], reply
    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    config = SubprocessConfig(working_dir="/work", claude_path="/usr/bin/claude", review_interval_seconds=0, **cfg)
    runner = SubprocessGoalRunner(config, settings=settings)
    return runner.run_goal(goal="make the thing", brief="do it", model="sonnet"), FakePopen.seen[-1]


def test_a_clean_run_is_met_with_its_usage_and_the_default_argv(monkeypatch):
    res, proc = run(monkeypatch, (0, envelope("all done"), ""))
    assert res.met and res.output == "all done" and res.tokens == 15 and res.cost_usd == 0.25
    assert proc.cmd[:4] == ["/usr/bin/claude", "-p", "--output-format", "json"]
    assert proc.cmd[proc.cmd.index("--model") + 1] == "sonnet" and "--session-id" in proc.cmd
    assert proc.stdin_text.startswith("TASK:\ndo it")


def test_the_consumers_marker_pauses_the_run_on_the_decision(monkeypatch):
    settings = GoalSettings(escalation_marker=MARKER)
    res, _ = run(monkeypatch, (0, envelope(f"asked.\n{MARKER} dec_77"), ""), settings)
    assert not res.met and res.decision_id == "dec_77"
    res, _ = run(monkeypatch, (0, envelope(f"asked.\n{MARKER} dec_77"), ""))
    assert res.met and res.decision_id is None   # no marker configured, so none is read


def test_the_child_environment_comes_from_the_settings(monkeypatch):
    def requester(env, user_id):
        env["WHO"] = str(user_id)
        return env

    settings = GoalSettings(run_id_env="MY_RUN_ID", apply_requester=requester,
                            environment=lambda: {"PATH": "/bin", "ANTHROPIC_API_KEY": "k", "CLAUDECODE": "1", "KEEP": "1"})
    FakePopen.seen, FakePopen.reply = [], (0, envelope("ok"), "")
    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    runner = SubprocessGoalRunner(SubprocessConfig(working_dir="/w", review_interval_seconds=0, extra_path_dirs=["/extra"]),
                                  settings=settings)
    runner.run_goal(goal="g", brief="b", run_id="abcd1234", requester_user_id="u1")
    env = FakePopen.seen[-1].kwargs["env"]
    assert env["MY_RUN_ID"] == "abcd1234" and env["WHO"] == "u1" and env["KEEP"] == "1" and env["PYTHONUNBUFFERED"] == "1"
    assert "ANTHROPIC_API_KEY" not in env and "CLAUDECODE" not in env and env["PATH"].startswith("/extra:")
    assert "MY_RUN_ID" not in SubprocessGoalRunner(SubprocessConfig(working_dir="/w")).build_env(run_id="x")


class Limits(UsageLimits):
    def __init__(self, active=None, found=None):
        self.active, self.found, self.recorded = active, found, []

    def active_limit(self):
        return self.active

    def detect_usage_limit(self, text):
        return self.found if "hit your" in text else None

    def record(self, limit):
        self.recorded.append(limit)
        return limit


def test_a_known_limit_refuses_to_spawn_and_keeps_the_session(monkeypatch):
    limit = SimpleNamespace(message="resets 1pm")
    FakePopen.seen = []
    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    runner = SubprocessGoalRunner(SubprocessConfig(working_dir="/w"), settings=GoalSettings(usage_limits=Limits(active=limit)))
    res = runner.run_goal(goal="g", brief="b", resume_session_id="sess-1")
    assert res.usage_limited and res.session_id == "sess-1" and "resets 1pm" in res.error and FakePopen.seen == []


def test_a_refusal_that_states_a_limit_is_recorded_and_not_a_failed_goal(monkeypatch):
    limit = SimpleNamespace(message="resets 8am")
    limits = Limits(found=limit)
    res, _ = run(monkeypatch, (1, envelope("You've hit your weekly limit", is_error=True), ""), GoalSettings(usage_limits=limits))
    assert res.usage_limited and limits.recorded == [limit] and "resets 8am" in res.error


def test_the_launch_flags_and_the_turn_cap_come_from_the_settings(monkeypatch):
    from hubofhubs.deep.launch import DeepLaunchSettings
    settings = GoalSettings(deep_launch=DeepLaunchSettings(strict_mcp=True, max_turns=6))
    _, proc = run(monkeypatch, (0, envelope("ok"), ""), settings)
    assert "--strict-mcp-config" in proc.cmd and proc.cmd[proc.cmd.index("--max-turns") + 1] == "6"


def test_a_worker_that_never_started_is_a_launch_failure_and_a_missing_binary_says_so(monkeypatch):
    refused = envelope("There's an issue with the selected model", is_error=True, usage={"input_tokens": 0, "output_tokens": 0})
    res, _ = run(monkeypatch, (1, refused, ""))
    assert res.launch_failed and "could not start" in res.error

    def missing(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "Popen", missing)
    res = SubprocessGoalRunner(SubprocessConfig(working_dir="/w", claude_path="claude-nowhere")).run_goal(goal="g", brief="b")
    assert res.launch_failed and res.launch_problem == "missing_program"


def test_running_out_of_turns_is_unconfirmed_and_resumable(monkeypatch):
    res, _ = run(monkeypatch, (1, envelope("partial", is_error=True, subtype="error_max_turns"), ""))
    assert not res.met and res.limit_hit and "UNCONFIRMED" in res.error and res.session_id
