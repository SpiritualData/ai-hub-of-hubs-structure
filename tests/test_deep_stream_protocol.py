"""The stream-json deep runner's protocol helpers and its steering bookkeeping (``hubofhubs.deep.stream_runner``): offline, no process."""
from __future__ import annotations

import json
import subprocess

from hubofhubs.deep.stream_runner import (
    MIN_STREAM_CONTROL_VERSION,
    Sent,
    StreamRun,
    cli_version,
    echo_text,
    interrupt_line,
    user_line,
)
from hubofhubs.ports.control import ControlMessage, RunControl


def test_stdin_lines_are_one_json_object_each():
    assert json.loads(user_line("hello")) == {"type": "user", "message": {"role": "user", "content": "hello"}}
    assert user_line("x").endswith("\n")
    line = json.loads(interrupt_line("int-1"))
    assert line["type"] == "control_request" and line["request_id"] == "int-1" and line["request"] == {"subtype": "interrupt"}


def test_only_a_replayed_user_message_has_echo_text_and_a_tool_result_has_none():
    assert echo_text({"message": {"content": "steer me"}}) == "steer me"
    assert echo_text({"message": {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}}) == "a\nb"
    assert echo_text({"message": {"content": [{"type": "tool_result", "content": "x"}]}}) is None
    assert echo_text({"message": {}}) is None


def test_the_version_is_read_once_per_binary_and_a_missing_binary_defers_to_the_launch(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=b"2.1.300 (Claude Code)\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", run)
    assert cli_version("/bin/claude-test-a", {}) == (2, 1, 300) and cli_version("/bin/claude-test-a", {}) == (2, 1, 300)
    assert len(calls) == 1 and (2, 1, 300) >= MIN_STREAM_CONTROL_VERSION

    def gone(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", gone)
    assert cli_version("/bin/claude-test-b", {}) == (999, 0, 0)


class FakeProc:
    stdout = stderr = stdin = None


def make_run(control, prompt="the opening prompt"):
    run = StreamRun.__new__(StreamRun)
    run.prompt, run.control, run.sent, run.clock = prompt, control, [], lambda: 1.0
    return run


def test_a_replay_marks_exactly_the_messages_it_contains_and_never_the_opening_prompt():
    seen = []
    control = RunControl(mark_seen=lambda ids, where: seen.append((list(ids), where)))
    run = make_run(control)
    run.sent = [Sent("m1", "go left", 0.0), Sent("m2", "go left", 0.0), Sent("m3", "stop", 0.0)]
    run.mark_replayed("the opening prompt")
    assert seen == [] and len(run.unseen()) == 3
    run.mark_replayed("go left")
    assert seen == [(["m1"], "deep_worker")] and run.unseen() == ["go left", "stop"]
    run.mark_replayed("go left\nand also stop")
    assert [r.seen_at for r in run.sent] == [1.0, 1.0, 1.0] and run.unseen() == []


def test_steering_claims_a_message_once_and_keeps_it_on_the_unseen_list_if_the_write_fails():
    written = []
    control = RunControl(claim_inputs=lambda: [ControlMessage("m1", "hello"), ControlMessage("m2", "  ")])
    run = make_run(control)
    run.finished = run.stopping = False
    run.write = lambda line: written.append(line) or False
    run.steer()
    assert [json.loads(w)["message"]["content"] for w in written] == ["hello"]
    assert run.unseen() == ["hello"]
    run.stopping = True
    run.steer()
    assert len(written) == 1
