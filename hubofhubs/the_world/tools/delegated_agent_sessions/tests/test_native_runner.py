"""The hub's frame on the model's own tool loop (``native_runner``): offline, the ``claude`` program is a fake script that speaks stream-json.

It records its argv and its first message, writes a file when told to, and ends with a result event the way the real CLI does."""
import json
import os
import shutil
import stat
import sys

import pytest

from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS, RULES, build_frame
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings, lean_flags
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import UNLIMITED, NativeToolLoopRunner, default_should_continue, outside_the_folder, session_actions, worth_resuming
from hubofhubs.the_world.tools.delegated_agent_sessions import native_runner
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
    if "slow" in text:      # a session that keeps working until it is steered (it then reports) or its input closes (the run was stopped)
        for more in sys.stdin:
            note = json.loads(more)
            if note.get("type") != "user":
                continue
            body = note["message"]["content"]
            body = body if isinstance(body, str) else " ".join(b.get("text", "") for b in body)
            with open(log, "a") as out:
                out.write(json.dumps({{"steer": body}}) + "\\n")
            if "safe stopping point" in body and os.environ.get("FAKE_MODE") != "stuck":
                print(json.dumps({{"type": "user", "message": {{"role": "user", "content": body}}}}), flush=True)
                print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "result": "wrapped up: two steps done, three left, resume from step three",
                                  "session_id": "sess-1", "total_cost_usd": 0.01, "usage": {{"input_tokens": 100, "output_tokens": 20}}}}), flush=True)
                sys.exit(0)
        sys.exit(0)
    if "write the report" in text:
        open("report.md", "w").write("The gate code is 4242.")
    reply = "done: figures fixed" if "code check" in text else "report written"
    # Like the real CLI, the cost is the session's running total: a resumed session reports the earlier turns too. Its ``usage`` is per turn (checked on a real
    # session: turn one 229 output tokens, the resumed turn 3, and the cost and ``modelUsage`` totals 232), so the tokens below are the same each turn and add up.
    launches = sum(1 for row in open(log) if '"argv"' in row)
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "result": reply, "session_id": "sess-1",
                      "total_cost_usd": 0.01 * launches, "usage": {{"input_tokens": 100, "output_tokens": 20}}}}), flush=True)
    break
'''


def fake_claude(tmp_path):
    path = tmp_path / "claude"
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def runner_for(tmp_path, monkeypatch, fake_mode="", **kwargs):
    work = tmp_path / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "notes.txt").write_text("the limit is 100\n")
    log = tmp_path / "log.jsonl"
    monkeypatch.setenv("FAKE_LOG", str(log))
    env = {"PATH": "/usr/bin:/bin", "FAKE_LOG": str(log), "FAKE_MODE": fake_mode}
    cfg = SubprocessConfig(working_dir=str(work), claude_path=fake_claude(tmp_path), review_interval_seconds=0, timeout_seconds=60)
    kwargs.setdefault("check_answer", False)       # the answer check makes its own launch; its tests (test_answer_check.py) turn it on
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
    assert argv[argv.index("--tools") + 1] == ",".join(NATIVE_TOOLS) + ",Agent"      # the general sub-agent tool is offered with the guard in place (test_general_helper.py)
    assert "--agents" in argv and "--settings" in argv
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
    assert got.met and got.output == "done: figures fixed" and got.tokens == 240 and got.cost_usd == pytest.approx(0.02)   # the session total after two turns, not 0.01 + 0.02


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


def test_the_arm_is_declared_paid_and_anthropic_only():
    assert NativeToolLoopRunner.PAID is True and NativeToolLoopRunner.PROVIDERS == ("anthropic",)


def test_a_figure_is_not_a_finding_when_the_folder_holds_data_the_check_cannot_read(tmp_path, monkeypatch):
    runner, log, work = runner_for(tmp_path, monkeypatch)
    (work / "store.db").write_bytes(b"SQLite\0format\0")       # the figure may come from here
    got = runner.run_goal(goal="write the report", brief="write the report on the notes")
    assert got.met and got.output == "report written" and len([r for r in records(log) if "argv" in r]) == 1


def test_worth_resuming_gates_by_kind_of_finding(tmp_path):
    (tmp_path / "a.txt").write_text("alpha\n")
    figure, named = "r.md: the figure 4242 is in no source file", "r.md: names the file x.csv, which is not in the folder"
    assert worth_resuming(str(tmp_path), [figure, named]) == [named, figure]          # all text: the check saw every source
    assert worth_resuming(str(tmp_path), [figure, named], "named_files") == [named]
    assert worth_resuming(str(tmp_path), [figure, named], "always") == [figure, named]
    (tmp_path / "data.bin").write_bytes(b"\0\1")
    assert worth_resuming(str(tmp_path), [figure, named]) == [named]                  # a binary source: a figure may live there
    assert worth_resuming(str(tmp_path), [figure, named], "always") == [figure, named]
    assert worth_resuming(str(tmp_path), []) == []


def flag(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


# --- the owner's four risks ------------------------------------------------------------------------------------------------------------

def test_no_ceiling_adds_no_spend_flag_and_a_ceiling_reaches_the_cli_and_shrinks_on_a_resume(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, ceiling_usd=UNLIMITED, ceiling_seconds=UNLIMITED)
    runner.run_goal(goal="write the report", brief="write the report on the notes")
    assert all("--max-budget-usd" not in r["argv"] for r in records(log) if "argv" in r)
    capped, log2, _w = runner_for(tmp_path / "b", monkeypatch, ceiling_usd=0.5, ceiling_turns=7)
    capped.run_goal(goal="write the report", brief="write the report on the notes")
    first, second = [r["argv"] for r in records(log2) if "argv" in r]
    assert flag(first, "--max-budget-usd") == "0.5" and flag(first, "--max-turns") == "7"
    assert flag(second, "--max-budget-usd") == "0.49"           # the run's ceiling less the $0.01 the first session spent


def test_a_ceiling_reached_stops_the_hubs_own_resume_and_says_why(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, ceiling_usd=0.01)
    got = runner.run_goal(goal="write the report", brief="write the report on the notes")
    assert len([r for r in records(log) if "argv" in r]) == 1 and got.end_reason == "resume_stopped:ceiling_spend"


def test_an_injected_decision_gates_every_resume_with_plain_facts(tmp_path, monkeypatch):
    seen = []

    def decide(facts):
        seen.append(dict(facts))
        return {"continue": facts["resumes"] < 2, "reason": "enough" if facts["resumes"] >= 2 else "again"}
    runner, log, _work = runner_for(tmp_path, monkeypatch, should_continue=decide)
    got = runner.run_goal(goal="write the report", brief="write the report on the notes")
    assert len([r for r in records(log) if "argv" in r]) == 3 and [f["resumes"] for f in seen] == [0, 1, 2]
    assert set(seen[0]) >= {"spend_usd", "turns", "resumes", "findings", "changed_outcome", "ceiling_usd", "ceiling_turns"}
    assert seen[0]["changed_outcome"] is None and seen[1]["changed_outcome"] is False and any("4242" in x for x in seen[0]["findings"])
    assert seen[2]["spend_usd"] == pytest.approx(0.03) and got.end_reason == "resume_stopped:enough"
    declined, log2, _w = runner_for(tmp_path / "c", monkeypatch, should_continue=lambda facts: False)
    assert declined.run_goal(goal="write the report", brief="write the report on the notes").end_reason == "resume_stopped:declined"
    assert len([r for r in records(log2) if "argv" in r]) == 1
    broken, log3, _w = runner_for(tmp_path / "d", monkeypatch, should_continue=lambda facts: 1 / 0)
    assert broken.run_goal(goal="write the report", brief="write the report on the notes").end_reason == "resume_stopped:decision_failed:ZeroDivisionError"


def test_the_default_decision_is_one_resume_for_a_code_finding_inside_the_ceiling():
    base = dict(spend_usd=0.0, turns=3, resumes=0, findings=["x"], changed_outcome=None, ceiling_usd=None, ceiling_turns=None)
    assert default_should_continue(base) == {"continue": True, "reason": "code_finding"}
    assert default_should_continue({**base, "findings": []})["reason"] == "no_code_finding"
    assert default_should_continue({**base, "resumes": 1})["reason"] == "resume_limit"
    assert default_should_continue({**base, "ceiling_usd": 1.0, "spend_usd": 1.0})["reason"] == "ceiling_spend"
    assert default_should_continue({**base, "ceiling_turns": 3})["reason"] == "ceiling_turns"


def test_the_usage_is_emitted_so_a_watcher_can_stop(tmp_path, monkeypatch):
    runner, _log, _work = runner_for(tmp_path, monkeypatch, ceiling_usd=1.0)
    events = []
    runner.run_goal(goal="write the report", brief="write the report on the notes", emit=events.append)
    usage = [e for e in events if e.type == "tokens"]
    assert len(usage) == 2 and usage[0].data["cost_usd"] == pytest.approx(0.01) and usage[1].data["resumes"] == 1 and usage[1].data["ceiling_usd"] == 1.0
    assert any(e.type == "status" and e.data.get("phase") == "hub_resume" for e in events)


def test_permission_setting_replaces_the_skip_flag_and_the_default_keeps_it(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch)
    runner.run_goal(goal="read the notes", brief="read the notes")
    assert "--dangerously-skip-permissions" in records(log)[0]["argv"] and "--permission-mode" not in records(log)[0]["argv"]
    asking, log2, _w = runner_for(tmp_path / "b", monkeypatch, permission="acceptEdits")
    assert asking.run_goal(goal="read the notes", brief="read the notes").met
    argv = records(log2)[0]["argv"]                              # the fake ran through the launcher, which added the mode flag
    assert flag(argv, "--permission-mode") == "acceptEdits" and "--dangerously-skip-permissions" not in argv
    with pytest.raises(ValueError):
        NativeToolLoopRunner(permission="anything")


def test_the_sandbox_wraps_the_session_in_the_hubs_bubblewrap_prefix(tmp_path, monkeypatch):
    if shutil.which("bwrap") is None:
        pytest.skip("bubblewrap is not installed")
    runner, _log, work = runner_for(tmp_path, monkeypatch, sandbox=True, sandbox_network=False)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    script = open(runner.write_launcher(folder_for_launcher=str(scratch), root=str(work)), encoding="utf-8").read()
    assert "\nexec bwrap " in script and "--ro-bind / /" in script and f"--bind {work} {work}" in script
    assert "--unshare-net" in script and script.rstrip().endswith('claude "$@"')


def test_a_session_that_wrote_or_ran_outside_the_folder_is_reported_not_refused(tmp_path, monkeypatch):
    work = str(tmp_path / "work")
    actions = [("Write", {"file_path": work + "/out.md"}), ("Write", {"file_path": "/etc/hosts"}), ("Edit", {"file_path": "/var/lib/elsewhere.txt"}),
               ("Bash", {"command": "python run.py > out.txt"}), ("Bash", {"command": "cp out.txt ~/saved.txt"}), ("Bash", {"command": "git push origin main"}),
               ("Read", {"file_path": "/etc/hosts"})]
    flags = outside_the_folder(work, actions)
    assert any("/etc/hosts" in f for f in flags) and any("elsewhere" in f for f in flags) and any("saved.txt" in f or "~" in f for f in flags)
    assert any("git push" in f for f in flags) and not any("out.md" in f or "run.py" in f for f in flags)
    record = tmp_path / "session.jsonl"
    record.write_text("\n".join(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": n, "input": i}]}}) for n, i in actions) + "\n{}\n")
    monkeypatch.setattr(native_runner, "find_session_file", lambda *a, **k: record)
    assert session_actions("s", work)[0] == len(actions) and session_actions("s", work)[1][0][0] == "Write"
    runner, _log, root = runner_for(tmp_path / "b", monkeypatch)
    got = runner.run_goal(goal="read the notes", brief="read the notes")
    assert got.met and any("/etc/hosts" in f for f in got.outside_folder)       # reported on the result, the run still met its goal


# --- the ceilings --------------------------------------------------------------------------------------------------------------------

def slow_runner(tmp_path, monkeypatch, mode="soft", **kwargs):
    runner, log, work = runner_for(tmp_path, monkeypatch, fake_mode=mode, **kwargs)
    runner.cfg.cancel_grace_seconds = 0.5
    runner.limit_poll_seconds = 0.05
    return runner, log, work


def test_defaults_are_on_and_unlimited_only_when_asked_for(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch)
    assert runner.ceiling_usd == native_runner.DEFAULT_CEILING_USD and runner.ceiling_seconds == native_runner.DEFAULT_CEILING_SECONDS
    assert 0 < runner.ceiling_usd <= 100 and 3600 <= runner.ceiling_seconds <= 24 * 3600 and 0.5 <= runner.soft_fraction < 1
    runner.run_goal(goal="read the notes", brief="read the notes")
    argv = records(log)[0]["argv"]
    assert flag(argv, "--max-budget-usd") == "20"                           # the CLI's own budget flag at the hard limit, a backstop
    free, log2, _w = runner_for(tmp_path / "u", monkeypatch, ceiling_usd=UNLIMITED, ceiling_seconds=UNLIMITED)
    assert free.ceiling_usd is None and free.ceiling_seconds is None
    free.run_goal(goal="read the notes", brief="read the notes")
    assert "--max-budget-usd" not in records(log2)[0]["argv"]
    for bad in (None, 0, -1, "no", True):
        with pytest.raises(ValueError):
            NativeToolLoopRunner(ceiling_usd=bad)
        with pytest.raises(ValueError):
            NativeToolLoopRunner(ceiling_seconds=bad)
    with pytest.raises(ValueError):
        NativeToolLoopRunner(soft_fraction=1.0)


def test_the_soft_limit_steers_once_and_the_run_ends_with_a_report(tmp_path, monkeypatch):
    runner, log, _work = slow_runner(tmp_path, monkeypatch, ceiling_seconds=2.0)
    events = []
    got = runner.run_goal(goal="slow job", brief="slow job", emit=events.append)
    steers = [r["steer"] for r in records(log) if "steer" in r]
    assert len(steers) == 1 and "safe stopping point" in steers[0] and "how to resume" in steers[0]
    assert got.met and "three left" in got.output and got.end_reason == "wrapped_up_at_soft_limit"
    assert got.session_id and got.session_id == got.resume_handle and got.spend_usd >= 0.01 and 1.0 <= got.elapsed_seconds < 4.0
    assert [e.data["phase"] for e in events if e.type == "status" and e.data.get("phase") == "soft_limit"] == ["soft_limit"]


def test_the_hard_limit_stops_and_returns_a_resumable_partial(tmp_path, monkeypatch):
    runner, log, _work = slow_runner(tmp_path, monkeypatch, mode="stuck", ceiling_seconds=1.0)
    got = runner.run_goal(goal="slow job", brief="slow job")
    assert len([r for r in records(log) if "steer" in r]) == 1          # it was asked once at the soft limit and did not stop
    assert not got.met and got.cancelled and got.end_reason == "stopped_at_hard_limit:time"
    assert got.session_id and got.resume_handle == got.session_id and got.elapsed_seconds >= 1.0 and "resume session" in got.error


def test_a_spend_limit_acts_the_same_way(tmp_path, monkeypatch):
    spent = {"now": 0.0}
    monkeypatch.setattr(native_runner, "estimate_spend", lambda path: spent["now"])
    runner, log, _work = slow_runner(tmp_path, monkeypatch, ceiling_usd=1.0)
    runner.local.estimated_at = 0.0
    monkeypatch.setattr(native_runner.NativeToolLoopRunner, "spend_now", lambda self, root: spent["now"])
    spent["now"] = 0.9                                                      # past the soft share of one dollar: asked once, and it reports
    got = runner.run_goal(goal="slow job", brief="slow job")
    assert got.end_reason == "wrapped_up_at_soft_limit" and len([r for r in records(log) if "steer" in r]) == 1
    stuck, log2, _w = slow_runner(tmp_path / "s", monkeypatch, mode="stuck", ceiling_usd=1.0)
    spent["now"] = 1.2
    cut = stuck.run_goal(goal="slow job", brief="slow job")
    assert cut.cancelled and cut.end_reason == "stopped_at_hard_limit:spend" and cut.session_id


def test_the_hubs_own_resume_counts_against_the_same_ceiling(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, ceiling_seconds=0.001)     # the soft share of the time is used before the check finishes
    got = runner.run_goal(goal="write the report", brief="write the report on the notes")
    assert len([r for r in records(log) if "argv" in r]) == 1 and got.end_reason == "resume_stopped:ceiling_time"
    facts = dict(spend_usd=0.0, turns=0, resumes=0, findings=["x"], changed_outcome=None, ceiling_usd=20.0, ceiling_seconds=100.0, elapsed_seconds=81.0, soft_fraction=0.8)
    assert default_should_continue(facts)["reason"] == "ceiling_time"
    assert default_should_continue({**facts, "elapsed_seconds": 79.0})["continue"] is True
    assert default_should_continue({**facts, "ceiling_seconds": None, "ceiling_usd": None, "elapsed_seconds": 10 ** 9})["continue"] is True   # unlimited: not gated by the ceilings


def test_a_tier_with_no_chosen_model_fails_the_launch_instead_of_running_on_the_balanced_default(tmp_path, monkeypatch):
    # A stored hard run had one case on the balanced model in a fast-tier run: the tier chooser returned no model for that construction and the launcher's own
    # balanced default filled the gap. A runner that names a tier now refuses to start without that tier's model, for each Claude Code runner.
    from hubofhubs.the_world.tools.delegated_agent_sessions import providers
    from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
    from hubofhubs.the_world.tools.delegated_agent_sessions.subprocess_runner import SubprocessGoalRunner
    monkeypatch.setattr(providers, "model_for", lambda provider, tier, folder=None: None)
    for index, cls in enumerate((NativeToolLoopRunner, StreamJsonGoalRunner, SubprocessGoalRunner)):
        runner, log, _work = runner_for(tmp_path / str(index), monkeypatch) if cls is NativeToolLoopRunner else (None, None, None)
        if runner is None:
            work = tmp_path / str(index) / "work"
            work.mkdir(parents=True)
            log = tmp_path / str(index) / "log.jsonl"
            monkeypatch.setenv("FAKE_LOG", str(log))
            cfg = SubprocessConfig(working_dir=str(work), claude_path=fake_claude(tmp_path / str(index)), timeout_seconds=60)
            runner = cls(cfg, settings=GoalSettings(environment=lambda: {"PATH": "/usr/bin:/bin", "FAKE_LOG": str(log)}), provider="anthropic", tier="fast")
        got = runner.run_goal(goal="write the report", brief="b")
        assert got.launch_failed and not got.met and "fast model" in got.error and not log.exists(), cls.__name__
