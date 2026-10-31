"""The goal contract of the deep runners (``hubofhubs.deep.contract``): offline, no process, no model call.

Settings are arguments, so each rule is exercised with a value in hand and no environment.
"""
from __future__ import annotations

import json
import subprocess

import pytest

from hubofhubs.deep.contract import (
    GoalRunner,
    SubprocessConfig,
    cli_safe_model,
    compose_goal_prompt,
    compose_goal_prompt_fitted,
    envelope_reports_no_work,
    extract_escalation_id,
    is_claude_model,
    parse_deep_review,
    parse_worker_output,
    resolve_deep_launch,
    resolve_deep_review_interval_seconds,
    resolve_deep_timeout_seconds,
    resume_target_missing,
    run_goal_accepts,
    stop_process_group,
)
from hubofhubs.deep.launch import DeepLaunchSettings
from hubofhubs.deep.settings import GoalSettings, resolve_goal_settings
from hubofhubs.ports.deep import DeepResult

MARKER = "WORKER-ESCALATED:"


def test_the_defaults_read_nothing_from_the_host():
    settings = GoalSettings()
    assert settings.deep_timeout_seconds is None and settings.deep_review_interval_seconds == 300.0
    assert settings.deep_launch.is_default() and settings.escalation_marker == "" and settings.run_id_env == ""
    assert settings.environment() == {} and settings.standing_instructions() == ""
    assert settings.usage_limits.active_limit() is None


def test_settings_are_a_value_or_a_callable_read_each_time():
    calls = []

    def source():
        calls.append(1)
        return GoalSettings(deep_timeout_seconds=len(calls))

    assert resolve_goal_settings(None).deep_review_interval_seconds == 300.0
    assert resolve_goal_settings(source).deep_timeout_seconds == 1
    assert resolve_goal_settings(source).deep_timeout_seconds == 2
    pinned = GoalSettings(deep_timeout_seconds=9)
    assert resolve_goal_settings(pinned) is pinned


def test_config_wins_over_settings_and_non_positive_means_off():
    settings = GoalSettings(deep_timeout_seconds=50, deep_review_interval_seconds=120, deep_launch=DeepLaunchSettings(strict_mcp=True))
    assert resolve_deep_timeout_seconds(None, settings) == 50 and resolve_deep_timeout_seconds(7, settings) == 7
    assert resolve_deep_timeout_seconds(0, settings) is None
    assert resolve_deep_review_interval_seconds(None, settings) == 120 and resolve_deep_review_interval_seconds(0, settings) is None
    pinned = DeepLaunchSettings(max_turns=3)
    assert resolve_deep_launch(None, settings).strict_mcp is True and resolve_deep_launch(pinned, settings) == pinned
    assert resolve_deep_timeout_seconds(None) is None and resolve_deep_review_interval_seconds(None) == 300.0


def test_the_escalation_marker_is_the_consumers_and_prose_is_not_an_escalation():
    out = f"did the work\nNote: {MARKER} dec_1234.\nmore\n{MARKER} <decision_id>\n"
    assert extract_escalation_id(out, MARKER) == "dec_1234"
    assert extract_escalation_id(f"print {MARKER} {{id}} when you escalate", MARKER) is None
    assert extract_escalation_id(out, "") is None and extract_escalation_id(out, "OTHER:") is None
    assert extract_escalation_id(f"{MARKER} a1b2 then {MARKER} zz99-final", MARKER) == "zz99-final"


def test_model_gating_is_a_pattern_and_a_translator_is_injected():
    assert is_claude_model("claude-sonnet-4-5") and is_claude_model("sonnet") and is_claude_model("us.anthropic.claude-x")
    assert not is_claude_model("gemini-3.5-flash") and not is_claude_model("")
    assert cli_safe_model("claude-sonnet") == "claude-sonnet" and cli_safe_model("gpt-4o") is None
    assert cli_safe_model("claude-sonnet", lambda m: "sonnet") == "sonnet"

    def broken(model):
        raise RuntimeError("boom")

    assert cli_safe_model("opus", broken) == "opus" and cli_safe_model("gpt-4o", broken) is None


def test_the_worker_envelope_is_read_and_a_no_work_failure_is_told_from_a_failed_run():
    raw = json.dumps({"result": "done", "usage": {"input_tokens": 3, "output_tokens": 4}, "total_cost_usd": 0.5,
                      "subtype": "success"})
    assert parse_worker_output(raw) == ("done", 7, 0.5, False, "success")
    assert parse_worker_output("plain text") == ("plain text", 0, 0.0, False, "")
    refused = json.dumps({"is_error": True, "result": "bad model", "usage": {"input_tokens": 0, "output_tokens": 0}})
    worked = json.dumps({"is_error": True, "result": "x", "usage": {"input_tokens": 5}})
    assert envelope_reports_no_work(refused) and not envelope_reports_no_work(worked)
    assert not envelope_reports_no_work("not json") and not envelope_reports_no_work(json.dumps({"is_error": True}))


def test_a_missing_resume_target_is_only_that():
    assert resume_target_missing(1, "", "No conversation found with session ID: abc")
    assert not resume_target_missing(0, "", "No conversation found")
    assert not resume_target_missing(1, "some output", "No conversation found")
    assert not resume_target_missing(1, "", "rate limited")


def test_the_review_verdict_is_parsed_or_none():
    assert parse_deep_review('x {"stop": true, "reason": "  stuck\\n here "} y') == (True, "stuck here")
    assert parse_deep_review('{"stop": false}') == (False, "No reason was given.")
    assert parse_deep_review('{"stop": "yes"}') is None and parse_deep_review("nothing") is None


class Budget:
    """A prompt budget that cuts the preamble to its first 5 characters, to see the budgeter used."""
    MIN_DEEP_PROMPT_TOKEN_BUDGET = 1

    def resolve_deep_prompt_budget(self, configured=None, *, model=None):
        return 100

    def fit_deep_prompt(self, preamble, task_parts, *, budget_tokens):
        return preamble[:5], task_parts, "FIT"


def test_the_prompt_carries_standing_instructions_task_goal_and_the_contract_in_order():
    settings = GoalSettings(standing_instructions=lambda: "STANDING")
    prompt = compose_goal_prompt("make  it\nwork", " do it ", preamble=" PREAMBLE ", settings=settings)
    parts = prompt.split("\n\n")
    assert parts[0] == "PREAMBLE" and parts[1] == "STANDING" and parts[2] == "TASK:\ndo it"
    assert parts[3] == "GOAL (the done-standard your work must satisfy):\nmake it work"
    assert parts[4].startswith("CONTEXT USAGE:") and parts[5].startswith("HEADLESS RUN CONTRACT:")
    assert parts[6].startswith("When done, summarize CONCRETELY")
    bare = compose_goal_prompt("", "just chat")
    assert "GOAL (" not in bare and bare.startswith("TASK:\njust chat")


def test_the_prompt_is_fitted_by_the_consumers_budgeter():
    text, fit = compose_goal_prompt_fitted("g", "b", preamble="PREAMBLE", settings=GoalSettings(prompt_budget=Budget()))
    assert text.startswith("PREAM\n\nTASK:") and fit == "FIT"


class Recorder:
    def __init__(self, result):
        self.result = result
        self.seen = None

    def run_goal(self, *, goal, brief, model=None, max_turns=None, context_preamble=None, **rest):
        self.seen = dict(goal=goal, max_turns=max_turns, context_preamble=context_preamble, rest=rest)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Narrow:
    def run_goal(self, *, goal, brief, model=None, max_turns=None):
        return DeepResult(met=True)


def test_the_wrapper_forwards_per_call_values_only_to_a_runner_that_accepts_them():
    wide = Recorder(DeepResult(met=True))
    GoalRunner(wide).run(goal="g", brief="b", context_preamble="p", working_dir="/w", resume_session_id="s")
    assert wide.seen["context_preamble"] == "p" and wide.seen["rest"] == {"working_dir": "/w", "resume_session_id": "s"}
    assert wide.seen["max_turns"] == 30
    assert run_goal_accepts(wide, "working_dir") and not run_goal_accepts(Narrow(), "working_dir")
    assert GoalRunner(Narrow()).run(goal="g", brief="b", context_preamble="p", working_dir="/w").met is True


def test_the_wrapper_never_raises_and_never_reports_met_with_an_error_or_a_decision():
    assert GoalRunner(Recorder(RuntimeError("x"))).run(goal="g", brief="b").error == "deep runner failed: RuntimeError"
    assert GoalRunner(Recorder(DeepResult(met=True, error="e"))).run(goal="g", brief="b").met is False
    assert GoalRunner(Recorder(DeepResult(met=True, decision_id="d1"))).run(goal="g", brief="b").met is False


def test_web_is_on_unless_tools_say_otherwise():
    assert SubprocessConfig(working_dir="/w").web_enabled()
    assert not SubprocessConfig(working_dir="/w", disallowed_tools=["WebFetch"]).web_enabled()
    assert not SubprocessConfig(working_dir="/w", allowed_tools=["Read"]).web_enabled()
    assert SubprocessConfig(working_dir="/w", allowed_tools=["Read", "WebSearch"]).web_enabled()


def test_a_worker_that_exits_on_interrupt_is_reported_interrupted():
    proc = subprocess.Popen(["sleep", "30"], start_new_session=True)
    out, err, how = stop_process_group(proc, grace_seconds=2.0)
    assert how == "interrupted" and proc.poll() is not None
