"""The general sub-agent of the selected arm, the channel to one running helper, and the helper events of the stream: every piece is pure code or a fake program, so no test here calls a model."""
import json
import os
import subprocess
import sys

from hubofhubs.the_consciousness.ai_session_experience.session_adapters import StreamJson
from hubofhubs.the_consciousness.ai_session_experience.session_events import AgentEnded, AgentStarted, Finished, MAIN, Step, Steer, Stop, Usage
from hubofhubs.the_consciousness.ai_session_experience.session_harnesses import StreamHarness
from hubofhubs.the_world.tools.delegated_agent_sessions import agent_channel, general_helper as helpers, solution_agents as agents
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import NativeToolLoopRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings


def runner_in(tmp_path, **kwargs):
    work = tmp_path / "work"
    work.mkdir()
    (work / "notes.txt").write_text("alpha\n")
    config = SubprocessConfig(working_dir=str(work))
    runner = NativeToolLoopRunner(config, settings=GoalSettings(environment=lambda: {}), provider="anthropic", tier="fast", session_dir=str(tmp_path / "sessions"), **kwargs)
    runner.model_of = lambda tier: "model-of-" + tier              # the chooser's pick of a model is not this test's business
    return runner, work


# --- the offer: a person who asks for a sub-agent gets one ----------------------------------------------------------------------------

def test_the_tier_of_the_helper_is_the_sub_agent_roles_and_no_model_is_named_here():
    asked = []

    def tier_of(role, requested=""):
        asked.append((role, requested))
        return "fast"
    assert helpers.sub_agent_model(lambda tier: "model-of-" + tier, "balanced", tier_of=tier_of) == "model-of-fast"
    assert asked == [("sub_agent", "balanced")]                    # the role table decides; the person's tier is only what the table's own rule may follow
    assert helpers.helper_definition(None) == {}                   # a tier with no model chosen gives no helper, never another tier's


def test_the_selected_arm_offers_the_helper_with_the_guard_and_the_channel(tmp_path):
    runner, work = runner_in(tmp_path)
    runner.prepare("find something", "find something", "", str(work), "key")
    assert helpers.HELPER in runner.local.tools[-1] or runner.local.tools[-1] == agents.AGENT_TOOL
    defined = json.loads(open(runner.local.agents_file).read())
    assert list(defined) == ["helper"] and defined["helper"]["model"].startswith("model-of-") and agents.AGENT_TOOL in defined["helper"]["tools"]      # it may start helpers of its own
    assert agent_channel.HELPER_RULE in defined["helper"]["prompt"]
    settings = json.loads(open(runner.local.settings_file).read())
    assert set(settings["hooks"]) == {"PreToolUse", "PostToolUse"} and runner.channel is not None
    frame = open(runner.local.frame_file).read()
    assert "SUB-AGENTS" in frame and 'subagent_type "helper"' in frame


def test_no_helper_when_the_budget_is_zero_or_the_tier_has_no_model(tmp_path):
    runner, work = runner_in(tmp_path, helper_calls=0)
    runner.prepare("g", "g", "", str(work), "key")
    assert runner.local.agents_file is None and agents.AGENT_TOOL not in runner.local.tools and runner.channel is None
    (tmp_path / "second").mkdir()
    other, work2 = runner_in(tmp_path / "second")
    other.model_of = lambda tier: None
    other.prepare("g", "g", "", str(work2), "key")
    assert other.local.agents_file is None


def guard_decision(tmp_path, data, allowed=("helper",), budget=2):
    path = tmp_path / "guard.py"
    path.write_text(agents.guard_script(allowed, budget, str(tmp_path / "count"), str(tmp_path / "log")))
    done = subprocess.run([sys.executable, str(path)], input=json.dumps(data), capture_output=True, text=True)
    return json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else None


def test_the_guard_allows_the_helper_in_the_foreground_to_any_depth_up_to_the_budget(tmp_path):
    call = {"tool_name": "Agent", "tool_input": {"subagent_type": "helper", "run_in_background": False}}
    assert guard_decision(tmp_path, call) is None and guard_decision(tmp_path, {**call, "agent_id": "a1"}) is None      # the main session and a helper may both call it
    spent = guard_decision(tmp_path, call)
    assert spent and spent["permissionDecision"] == "deny" and "budget of 2" in spent["permissionDecisionReason"]
    assert "only its solution agents" in guard_decision(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "run_in_background": False}})["permissionDecisionReason"]


# --- the channel: a message to one running helper, and a stop of it alone -----------------------------------------------------------------

def hook(tmp_path, data):
    script = tmp_path / "hook.py"
    script.write_text(agent_channel.hook_script(str(tmp_path / "channel")))
    done = subprocess.run([sys.executable, str(script)], input=json.dumps(data), capture_output=True, text=True)
    return json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else None


def test_a_message_reaches_the_helper_it_names_at_its_next_tool_call_and_no_other(tmp_path):
    channel = agent_channel.AgentChannel(str(tmp_path / "channel"))
    assert channel.send("a1", "use the short name", "m1") and channel.send("a1", "and skip the tests", "m2") and not channel.send("", "x", "m3")
    other = hook(tmp_path, {"hook_event_name": "PostToolUse", "agent_id": "a2"})
    main = hook(tmp_path, {"hook_event_name": "PostToolUse"})
    assert other is None and main is None and channel.delivered() == []             # another helper and the main session read nothing
    got = hook(tmp_path, {"hook_event_name": "PostToolUse", "agent_id": "a1"})
    assert got["hookEventName"] == "PostToolUse" and got["additionalContext"].splitlines() == [agent_channel.PERSON_MESSAGE + " use the short name", agent_channel.PERSON_MESSAGE + " and skip the tests"]
    assert channel.delivered() == [("a1", "m1"), ("a1", "m2")] and channel.delivered() == []        # reported as taken up once
    assert hook(tmp_path, {"hook_event_name": "PostToolUse", "agent_id": "a1"}) is None             # and read once


def test_a_stop_refuses_only_that_helpers_next_call(tmp_path):
    channel = agent_channel.AgentChannel(str(tmp_path / "channel"))
    assert channel.stop("a1")
    stopped = hook(tmp_path, {"hook_event_name": "PreToolUse", "agent_id": "a1", "tool_name": "Read"})
    assert stopped["permissionDecision"] == "deny" and "stopped you" in stopped["permissionDecisionReason"]
    assert hook(tmp_path, {"hook_event_name": "PreToolUse", "agent_id": "a2", "tool_name": "Read"}) is None
    assert hook(tmp_path, {"hook_event_name": "PreToolUse", "tool_name": "Read"}) is None          # the main session is not a helper: its stop is the stream's


def test_the_runner_steers_and_stops_a_helper_by_the_task_id_and_says_when_it_was_read(tmp_path):
    runner, work = runner_in(tmp_path)
    assert runner.steer_agent("a1", "hello") is False and runner.stop_agent("a1") is False            # nothing offered yet
    runner.prepare("g", "g", "", str(work), "key")
    assert runner.steer_agent("a1", "hello", "m1") and runner.stop_agent("a1")
    script = os.path.join(os.path.dirname(runner.local.agents_file), "agent-hook.py")          # the hook the session runs, written for this run's channel
    read = subprocess.run([sys.executable, script], input=json.dumps({"hook_event_name": "PostToolUse", "agent_id": "a1"}), capture_output=True, text=True)
    assert "hello" in json.loads(read.stdout)["hookSpecificOutput"]["additionalContext"]
    assert runner.delivered_messages() == [("a1", "m1")] and runner.delivered_messages() == []
    refused = subprocess.run([sys.executable, script], input=json.dumps({"hook_event_name": "PreToolUse", "agent_id": "a1"}), capture_output=True, text=True)
    assert json.loads(refused.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- the stream: every helper at every depth, with its parent, its figures and its result ---------------------------------------------

def task_line(subtype, task, tool, **more):
    return {"type": "system", "subtype": subtype, "task_id": task, "tool_use_id": tool, "task_type": "local_agent", **more}


def tool_use(name, ident, parent=None, **given):
    return {"type": "assistant", "parent_tool_use_id": parent, "message": {"content": [{"type": "tool_use", "name": name, "id": ident, "input": given}]}}


def test_helpers_at_depth_one_two_and_three_carry_their_parents_figures_and_results():
    stream = StreamJson()
    out = []
    out += stream.events(tool_use("Agent", "tu1", description="survey", subagent_type="helper"))
    out += stream.events(task_line("task_started", "t1", "tu1", description="survey"))
    out += stream.events(tool_use("Agent", "tu2", parent="tu1", description="check the moon", subagent_type="helper"))     # depth 2 is in the stream as the first helper's own message
    out += stream.events(task_line("task_started", "t2", "tu2", description="check the moon", parent_task_id="t1"))
    out += stream.events(task_line("task_started", "t3", "tu3", description="read soil", parent_task_id="t2"))             # depth 3 is only in the task lines
    out += stream.events(task_line("task_progress", "t3", "tu3", description="Reading soil.md", usage={"total_tokens": 900, "tool_uses": 1}))
    out += stream.events(task_line("task_notification", "t3", "tu3", status="completed", summary="soil is clay", usage={"total_tokens": 1500, "tool_uses": 2}))
    out += stream.events({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "tu2", "content": [{"type": "text", "text": "the moon note"}]}]}})
    out += stream.events(task_line("task_notification", "t2", "tu2", status="completed", summary="the moon note"))          # the same end is told twice: one event
    started = {e.agent_id: e.parent_id for e in out if isinstance(e, AgentStarted)}
    assert started == {"tu1": MAIN, "tu2": "tu1", "tu3": "tu2"}
    assert stream.task_ids == {"tu1": "t1", "tu2": "t2", "tu3": "t3"}
    ended = [e for e in out if isinstance(e, AgentEnded)]
    assert [e.agent_id for e in ended] == ["tu3", "tu2"] and ended[0].summary == "soil is clay" and ended[0].tokens == 1500 and ended[0].calls == 2
    assert any(isinstance(e, Usage) and e.agent_id == "tu3" and e.tokens == 900 for e in out)
    assert any(isinstance(e, Step) and e.agent_id == "tu3" and e.label == "Reading soil.md" for e in out)                  # activity of a helper the stream shows no messages of
    assert "tu1" in stream.open_agents and "tu2" not in stream.open_agents


# --- the harness: a message or a stop aimed at one helper reaches that helper and nothing else --------------------------------------------------

class FakeRunner:
    by_task_id = True

    def __init__(self):
        self.sent, self.stopped, self.taken = [], [], []

    def steer_agent(self, task_id, text, message_id=""):
        self.sent.append((task_id, text, message_id))
        return True

    def stop_agent(self, task_id):
        self.stopped.append(task_id)
        return True

    def delivered_messages(self):
        got, self.taken = self.taken, []
        return got

    def run_goal(self, goal, brief, emit, run_id, resume_session_id=None, cancel_check=None, control=None):
        from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent
        lines = [tool_use("Agent", "tu1", description="one"), task_line("task_started", "t1", "tu1", description="one"),
                 tool_use("Agent", "tu2", parent="tu1", description="two"), task_line("task_started", "t2", "tu2", description="two", parent_task_id="t1")]
        for line in lines:
            emit(ProgressEvent(type="stream", text="", data=line))
        self.harness.probe = True
        self.release.wait(5)
        for line in (task_line("task_notification", "t2", "tu2", status="completed", summary="two"), task_line("task_notification", "t1", "tu1", status="completed", summary="one")):
            emit(ProgressEvent(type="stream", text="", data=line))
        return DeepResult(output="done", met=True, cost_usd=0.0, tokens=0)


def test_steer_and_stop_name_the_helper_and_are_shown_only_when_taken(tmp_path):
    import threading
    runner = FakeRunner()
    harness = StreamHarness(runner)
    runner.harness, runner.release = harness, threading.Event()
    events = []
    thread = threading.Thread(target=lambda: harness.start("go", events.append), daemon=True)
    thread.start()
    for _ in range(100):
        if harness.stream is not None and "tu2" in harness.stream.task_ids:
            break
        threading.Event().wait(0.05)
    assert harness.control(Steer(text="use the short name", agent_id="tu2", message_id="m1"))
    assert runner.sent == [("t2", "use the short name", "m1")]                              # the CLI's id of that helper, not its parent's and not the run's
    assert not [e for e in events if isinstance(e, Step) and e.kind == "message-received"]    # queued until the helper has read it
    runner.taken = [("t2", "m1")]
    for _ in range(60):
        if any(isinstance(e, Step) and e.kind == "message-received" for e in events):
            break
        threading.Event().wait(0.05)
    got = [e for e in events if isinstance(e, Step) and e.kind == "message-received"]
    assert got and got[0].agent_id == "tu2" and got[0].step_id == "m1"                     # taken up, said to be for that helper
    assert harness.control(Stop(agent_id="tu1"))
    assert sorted(runner.stopped) == ["t1", "t2"]                                          # the helper and the helper under it; the run is untouched
    assert not harness.stopped.is_set()
    assert not harness.control(Steer(text="x", agent_id="never-announced"))                  # a helper the stream has not announced cannot be reached: the surface tries again
    runner.release.set()
    thread.join(5)
    assert isinstance(events[-1], Finished) and events[-1].outcome == "met"


def test_stopping_a_helper_also_uses_the_clis_own_stop_of_that_task():
    from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import stop_task_line

    class Run:
        def __init__(self):
            self.lines = []

        def write(self, line):
            self.lines.append(line)
            return True
    sent = json.loads(stop_task_line("r1", "t9"))
    assert sent == {"type": "control_request", "request_id": "r1", "request": {"subtype": "stop_task", "task_id": "t9"}}
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as folder:
        runner, work = runner_in(pathlib.Path(folder))
        assert runner.stop_task("t9") is False                    # no session in flight
        runner.live_run = Run()
        runner.prepare("g", "g", "", str(work), "key")
        assert runner.stop_agent("t9") and json.loads(runner.live_run.lines[0])["request"] == {"subtype": "stop_task", "task_id": "t9"}
        assert os.path.exists(os.path.join(runner.channel.folder, "stop-t9"))      # and the soft refusal stays as the fallback
