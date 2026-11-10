"""The hub loop reports the session contract's events itself, and a stop does not wait for the model call in flight: scripted completion, no model."""
import subprocess
import sys
import threading
import time
from pathlib import Path

from hubofhubs.the_intelligence.mind.delegation.solution_workers import work_solution
from hubofhubs.the_world.model_plumbing.vendor_model_caller import claude_cli
from hubofhubs.the_world.tools.deep import ProgressEvent
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import Telling, run_loop
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner, as_solution_worker

FENCE_OPEN, DIVIDER, FENCE_CLOSE = "<" * 7 + " SEARCH", "=" * 7, ">" * 7 + " REPLACE"


def edit(path, search, replace):
    return f"{path}\n{FENCE_OPEN}\n{search}{DIVIDER}\n{replace}{FENCE_CLOSE}\n"


class Script:
    """A completion that answers from a list of replies."""

    def __init__(self, *replies):
        self.replies = list(replies)

    def __call__(self, system, prompt):
        return self.replies.pop(0) if self.replies else "BLOCKED: script ended"


def folder(tmp_path: Path, **files: str) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


def collect():
    got = []
    return got, Telling(got.append)


def test_a_step_per_action_runs_then_ends_and_usage_follows_each_call(tmp_path):
    root = folder(tmp_path, **{"app.py": "x = 1\n"})
    got, tell = collect()
    reply = edit("app.py", "x = 1\n", "x = 2\n") + "RUN: echo hi\nCHECK: grep -q 'x = 2' app.py\nREPORT: done\n"
    assert run_loop("Set x", working_dir=root, complete=Script(reply), telling=tell).met
    steps = [(e["kind"], e["state"]) for e in got if e["type"] == "step"]
    assert steps == [("edit", "done"), ("run", "running"), ("run", "done"), ("check", "running"), ("check", "done")]
    running = next(e for e in got if e["type"] == "step" and e["state"] == "running" and e["kind"] == "run")
    ended = next(e for e in got if e["type"] == "step" and e["state"] == "done" and e["kind"] == "run")
    assert running["step_id"] == ended["step_id"] and ended["label"] == "echo hi" and all(e["agent_id"] == "main" for e in got)
    assert [e["calls"] for e in got if e["type"] == "usage"] == [1]


def test_a_failed_action_says_why(tmp_path):
    root = folder(tmp_path)
    got, tell = collect()
    run_loop("Run it", working_dir=root, complete=Script("RUN: exit 3\nREPORT: done\n", "BLOCKED: x"), telling=tell)
    failed = [e for e in got if e["type"] == "step" and e["state"] == "failed"]
    assert failed and "exit 3" in failed[0]["detail"]


def test_a_message_taken_from_the_inbox_is_a_step_of_its_own(tmp_path):
    root = folder(tmp_path)
    got, tell = collect()
    pending = ["use the short name"]
    run_loop("Work", working_dir=root, complete=Script("NOTE: ok\nRUN: echo a\n", "REPORT: done\n"), telling=tell, inbox=lambda: [pending.pop()] if pending else [])
    taken = [e for e in got if e["type"] == "step" and e["kind"] == "message-received"]
    assert len(taken) == 1 and taken[0]["label"] == "use the short name"


def test_a_helper_is_announced_under_its_parent_with_its_own_steps(tmp_path):
    root = folder(tmp_path)
    got, tell = collect()
    parent = "DELEGATE: write the tests\n"
    child = edit("tests.txt", "", "ok\n") + "REPORT: tests done\n"
    run_loop("Ship", working_dir=root, complete=Script(parent, child, "REPORT: shipped\n"), telling=tell, review=False)
    started = next(e for e in got if e["type"] == "agent-started")
    ended = next(e for e in got if e["type"] == "agent-ended")
    inner = next(e for e in got if e["type"] == "step" and e["kind"] == "edit")
    assert started["parent_id"] == "main" and started["task"] == "write the tests" and inner["agent_id"] == started["agent_id"] == ended["agent_id"]
    assert got.index(started) < got.index(inner) < got.index(ended) and ended["state"] == "met"


def test_the_runner_reports_the_run_start_with_its_solution_and_the_cost_so_far(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    runner = SolutionLoopRunner(root=root, complete=Script("It is a."), sandbox=False, review=False, session_dir=str(tmp_path / "s"))
    seen = []
    runner.work("What is in a.txt?", emit=seen.append, solution="notes", milestone="notes are right", frame="Be exact.")
    sessions = [e.data for e in seen if e.type == "session"]
    start = sessions[0]
    assert start["type"] == "run-started" and (start["solution"], start["milestone"], start["frame"]) == ("notes", "notes are right", "Be exact.")
    assert any(d["type"] == "usage" and d["calls"] == 1 for d in sessions)


def test_a_solution_tree_is_a_tree_of_agents_with_their_solutions_and_steps(tmp_path):
    root = folder(tmp_path)
    runner = SolutionLoopRunner(root=root, complete=lambda s, p: "REPORT: ok\n" if "Solution:" in p else "", sandbox=False, review=False, session_dir=str(tmp_path / "s"))
    events = []
    worker = as_solution_worker(runner, root, emit=lambda e: events.append(e.data) if e.type == "session" else None)
    tree = work_solution("top", frame=lambda sid: {"name": sid.title(), "milestone": "m"}, children=lambda sid, task: ["leaf"] if sid == "top" else [],
                         work=worker, check=lambda sid, m, out: {"met": True}, session=events.append)
    assert tree.met
    started = {e["solution"]: (e["agent_id"], e["parent_id"]) for e in events if e["type"] == "agent-started"}
    assert started == {"top": ("top", "main"), "leaf": ("top-leaf", "top")}
    usage_agents = {e["agent_id"] for e in events if e["type"] == "usage"}
    assert usage_agents == {"top", "top-leaf"} and sum(e["type"] == "agent-ended" for e in events) == 2


def test_a_stop_during_a_slow_model_call_returns_at_once_and_the_session_resumes(tmp_path):
    root = folder(tmp_path)
    release = threading.Event()
    calls = []

    def slow(system, prompt):
        calls.append(prompt)
        if len(calls) == 2 and not release.is_set():
            release.wait(8)
            return "REPORT: late\n"
        return edit(f"f{len(calls)}.txt", "", "x\n") + ("REPORT: done\n" if len(calls) >= 3 else "")
    runner = SolutionLoopRunner(root=root, complete=slow, sandbox=False, review=False, session_dir=str(tmp_path / "s"))
    stop = threading.Event()
    threading.Timer(0.3, stop.set).start()
    began = time.monotonic()
    result, _usage, why = runner.work("make files", cancel_check=stop.is_set, session_id="s1", run_id="r1")
    assert why == "cancelled" and time.monotonic() - began < 2.5 and (tmp_path / "f1.txt").exists()
    release.set()
    again, _u, _w = runner.work("make files", session_id="s1", resume_session_id="s1", run_id="r2")
    assert again.met and (tmp_path / "f3.txt").exists() and "late" not in again.report


def test_abandoning_a_completion_kills_its_process_group_at_once():
    began = time.monotonic()
    box = {}

    def go():
        try:
            claude_cli.run_in_group([sys.executable, "-c", "import time; time.sleep(30)"], input="", env=None, cwd=None, timeout=60)
        except BaseException as error:  # noqa: BLE001
            box["error"] = error
    worker = threading.Thread(target=go)
    worker.start()
    while worker.ident not in claude_cli.RUNNING and time.monotonic() - began < 5:
        time.sleep(0.02)
    assert claude_cli.abandon_thread(worker.ident) is True
    worker.join(5)
    assert not worker.is_alive() and time.monotonic() - began < 6 and worker.ident not in claude_cli.RUNNING


def test_a_run_control_steers_and_pauses_the_loop_like_the_stream_runner(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions.control import ControlMessage, RunControl
    root = folder(tmp_path)
    prompts, seen, pause = [], [], threading.Event()
    sent = [[ControlMessage("m1", "use the short name")]]

    def complete(system, prompt):
        prompts.append(prompt)
        if len(prompts) == 2:
            pause.set()
        return "RUN: echo step\n"
    control = RunControl(claim_inputs=lambda: sent.pop(0) if sent else [], mark_seen=lambda ids, where: seen.append((ids, where)), pause_requested=pause.is_set)
    runner = SolutionLoopRunner(root=root, complete=complete, sandbox=False, review=False, session_dir=str(tmp_path / "s"))
    deep = runner.run_goal(goal="work", control=control, run_id="r1")
    assert seen == [(["m1"], "deep_worker")] and "use the short name" in prompts[0]
    assert deep.paused and deep.cancelled and deep.session_id == "r1"
