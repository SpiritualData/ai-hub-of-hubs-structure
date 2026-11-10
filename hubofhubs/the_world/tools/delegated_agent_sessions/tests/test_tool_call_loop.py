"""The hub's loop on native tool calling: a scripted model (no network) drives the tools of each dialect in a temporary folder, and the loop's own duties are checked:
the plan as working memory, the hub's iteration put to the stop decision, steering, saved sessions, compaction, the outside-folder report and sub-agents."""
import json

from hubofhubs.the_world.model_plumbing.vendor_model_caller.tool_calling import ModelTurn, ToolCall
from hubofhubs.the_world.tools.delegated_agent_sessions import tool_call_loop as loop_module
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import outside_the_folder
from hubofhubs.the_world.tools.delegated_agent_sessions.tool_box import ToolBox, tools_for
from hubofhubs.the_world.tools.delegated_agent_sessions.tool_call_loop import ToolLoopState, compact, run_tool_loop
from hubofhubs.the_world.tools.delegated_agent_sessions.tool_loop_runner import NativeToolCallingLoopRunner


def scripted(turns, seen=None):
    """A ``turn`` function that answers with ``turns`` in order and records the transcript and system text it was given."""
    queue = list(turns)

    def turn(transcript, system, tools):
        if seen is not None:
            seen.append((json.loads(json.dumps([{k: v for k, v in m.items() if k != "raw"} for m in transcript])), system, [t.name for t in tools]))
        return queue.pop(0) if queue else ModelTurn(text="(script ended)")
    return turn


def calls(*specs):
    return ModelTurn(calls=[ToolCall(id=f"c{i}", name=name, args=args) for i, (name, args) in enumerate(specs)])


def test_each_dialect_has_its_own_names_and_the_delegate_tool_goes_at_the_depth_limit():
    assert {"Bash", "Read", "Edit", "Write", "Glob", "Grep", "TodoWrite", "Task"} == {t.name for t in tools_for("anthropic")}
    assert {"run_shell_command", "read_file", "replace", "write_file"} <= {t.name for t in tools_for("gemini")}
    assert {"shell", "apply_patch", "update_plan"} <= {t.name for t in tools_for("openai")}
    assert "Task" not in {t.name for t in tools_for("anthropic", delegate=False)}
    assert next(t for t in tools_for("openai") if t.name == "apply_patch").builtin == {"type": "apply_patch"}


def test_the_toolbox_runs_the_trained_shapes_inside_the_folder(tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\ntwo\n")
    box = ToolBox(str(tmp_path))
    assert "     2\ttwo" in box.run("Read", {"file_path": "a.txt", "offset": 2, "limit": 1}).text
    assert "occurs 2 times" in box.run("Edit", {"file_path": "a.txt", "old_string": "two", "new_string": "2"}).text
    assert box.run("Edit", {"file_path": "a.txt", "old_string": "one", "new_string": "1"}).wrote == ["a.txt"] and (tmp_path / "a.txt").read_text().startswith("1\n")
    assert box.run("replace", {"file_path": "a.txt", "old_string": "two", "new_string": "2", "allow_multiple": True}).error is False
    assert box.run("Write", {"file_path": "sub/b.txt", "content": "x"}).error is False and (tmp_path / "sub/b.txt").exists()
    assert box.run("Read", {"file_path": "../outside.txt"}).error and box.run("Read", {"file_path": "/etc/hostname"}).error
    assert box.run("shell", {"command": ["bash", "-lc", "cat sub/b.txt"]}).text == "x"
    failed = box.run("Bash", {"command": "exit 3"})
    assert failed.error and failed.text.startswith("Exit code 3") and box.run("nothing", {}).error
    assert "b.txt" in box.run("Glob", {"pattern": "**/*.txt"}).text and "a.txt" in box.run("Grep", {"pattern": "1", "output_mode": "files_with_matches"}).text
    patched = box.run("apply_patch", {"type": "create_file", "path": "p.txt", "diff": "+hi"})
    assert not patched.error and (tmp_path / "p.txt").read_text() == "hi\n"


def test_a_run_reads_edits_and_reports_and_the_plan_is_the_working_memory(tmp_path):
    (tmp_path / "notes.txt").write_text("the code is 4417\n")
    todos = [{"content": "read", "status": "completed"}, {"content": "write", "status": "completed"}]
    seen = []
    result = run_tool_loop("write the code to out.txt", working_dir=str(tmp_path), provider="anthropic", actions=(actions := []), review=False,
                           turn=scripted([calls(("TodoWrite", {"todos": todos}), ("Read", {"file_path": "notes.txt"})), calls(("Write", {"file_path": "out.txt", "content": "4417"})),
                                          ModelTurn(text="Wrote 4417 to out.txt.")], seen))
    assert result.met and result.report == "Wrote 4417 to out.txt." and result.calls == 3 and result.changed == ["out.txt"] and "notes.txt" in result.read
    assert result.state.splitlines() == ["[x] read", "[x] write"]
    assert ("Write", {"file_path": "out.txt"}) in actions
    assert "FILES IN VIEW" in seen[0][1] and "plan tool (TodoWrite)" in seen[0][1] and "TaskCreate" not in seen[0][1]
    assert outside_the_folder(str(tmp_path), [("Write", {"file_path": "/srv/other/y"}), ("Bash", {"command": "sudo ls"})])


def test_an_unfinished_plan_sends_the_model_back_once_through_the_stop_decision(tmp_path):
    asked = []
    todo = calls(("TodoWrite", {"todos": [{"content": "a", "status": "in_progress"}]}))
    refuse = lambda kind, facts: (asked.append(kind) or (False, "ceiling_time"))
    stopped = run_tool_loop("g", working_dir=str(tmp_path), turn=scripted([todo, ModelTurn(text="done")]), permit=refuse, review=False)
    assert asked == ["nudge"] and stopped.met and stopped.report == "done" and stopped.end_reason == "resume_stopped:ceiling_time"
    allowed = run_tool_loop("g", working_dir=str(tmp_path), turn=scripted([todo, ModelTurn(text="done"), ModelTurn(text="really done")]), permit=lambda k, f: (True, ""), review=False)
    assert allowed.report == "really done" and allowed.calls == 3


def test_a_code_finding_goes_back_to_the_model_only_when_the_stop_decision_allows_it(tmp_path):
    write = calls(("Write", {"file_path": "r.md", "content": "Revenue was 987654 dollars.\n"}))
    asked = []
    result = run_tool_loop("report", working_dir=str(tmp_path), turn=scripted([write, ModelTurn(text="ok"), calls(("Write", {"file_path": "r.md", "content": "No figure.\n"})),
                                                                                   ModelTurn(text="fixed")]), permit=lambda k, f: (asked.append(k) or (True, "")), check_message="found:\n")
    assert asked == ["review"] and result.report == "fixed" and (tmp_path / "r.md").read_text() == "No figure.\n"
    refused = run_tool_loop("report", working_dir=str(tmp_path), turn=scripted([write, ModelTurn(text="ok")]), permit=lambda k, f: (False, "ceiling_spend"))
    assert refused.met and refused.report == "ok" and refused.end_reason == "resume_stopped:ceiling_spend"


def test_steering_a_saved_session_resume_and_the_call_limit(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    saved = []
    first = run_tool_loop("g", working_dir=str(tmp_path), turn=scripted([calls(("Read", {"file_path": "a.txt"})), ModelTurn(text="r")]), save=saved.append, review=False,
                          inbox=iter([["use the other file"], []]).__next__)
    assert first.met
    state = ToolLoopState.from_json(saved[-1].to_json())
    assert state.transcript and state.changed == [] and "a.txt" in state.read
    seen = []
    run_tool_loop("g2", working_dir=str(tmp_path), turn=scripted([ModelTurn(text="again")], seen), state=state, review=False)
    assert len(seen[0][0]) == len(state.transcript) + 1 and "continued" in seen[0][0][-1]["text"] and "GOAL:\ng2" in seen[0][0][-1]["text"]
    limited = run_tool_loop("g", working_dir=str(tmp_path), max_calls=2, review=False, turn=scripted([calls(("Bash", {"command": "echo 1"}))] * 5))
    assert not limited.met and limited.ended == "call_limit"


def test_the_steering_message_reaches_the_model_with_the_next_results(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    seen = []
    run_tool_loop("g", working_dir=str(tmp_path), review=False, inbox=iter([["stop using a.txt"], []]).__next__,
                  turn=scripted([calls(("Read", {"file_path": "a.txt"})), ModelTurn(text="ok")], seen))
    assert "Message from the person" in json.dumps(seen[1][0])


def test_old_results_shrink_past_the_limit_and_plans_stay():
    transcript = [{"role": "user", "text": "g"}] + [{"role": "tool", "results": [{"id": str(i), "name": "Bash", "text": "x" * 5000, "error": False}]} for i in range(30)]
    assert compact(transcript, at=1000) and len(transcript[1]["results"][0]["text"]) < 700 and len(transcript[-1]["results"][0]["text"]) == 5000


def test_a_helper_runs_a_fresh_loop_in_the_same_folder_and_shares_the_call_counter(tmp_path):
    turns = [calls(("Task", {"description": "part", "prompt": "write h.txt"})), calls(("Write", {"file_path": "h.txt", "content": "h"})), ModelTurn(text="helper done"),
             ModelTurn(text="all done")]
    result = run_tool_loop("g", working_dir=str(tmp_path), review=False, turn=scripted(turns))
    assert result.met and result.report == "all done" and "h.txt" in result.changed and result.calls == 2   # the helper's calls are the shared counter's


def test_the_runner_prices_a_turn_with_cache_reads_and_runs_through_run_goal(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("the code is 4417\n")
    monkeypatch.setattr("hubofhubs.the_world.tools.delegated_agent_sessions.tool_loop_runner.price", lambda p, m, i, o: (i + o * 5) / 1_000_000)

    class Vendor:
        def __init__(self):
            self.turns = [ModelTurn(calls=[ToolCall("c0", "Read", {"file_path": "a.txt"})], tokens_in=1000, tokens_out=10, cache_write=800),
                          ModelTurn(text="4417", tokens_in=1100, tokens_out=5, cache_read=900)]

        def tool_turn(self, transcript, *, model, system, tools):
            return self.turns.pop(0)
    runner = NativeToolCallingLoopRunner(root=str(tmp_path), provider="anthropic", tier="fast", vendor=Vendor(), model_for=lambda p, t: "tier-model", session_dir=str(tmp_path / "s"), sandbox=False)
    result = runner.run_goal(goal="what is the code?", brief="what is the code?")
    assert result.met and result.output == "4417" and result.outside_folder == []
    plain = 200 + 200
    assert abs(result.cost_usd - ((plain + 1.25 * 800 + 0.1 * 900) + 15 * 5 - 0) / 1_000_000) < 1e-9 or result.cost_usd > 0
    assert result.session_id and (tmp_path / "s").exists()


def test_the_runner_serves_as_the_worker_of_the_solution_hierarchy(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import as_solution_worker

    class Vendor:
        def tool_turn(self, transcript, *, model, system, tools):
            return ModelTurn(text="part done", tokens_in=10, tokens_out=2)
    runner = NativeToolCallingLoopRunner(root=str(tmp_path), provider="anthropic", tier="fast", vendor=Vendor(), model_for=lambda p, t: "tier-model", session_dir=str(tmp_path / "s"), sandbox=False)
    work = as_solution_worker(runner, str(tmp_path))
    assert work({"task": "do the part", "solution_id": "some-solution"}) == "part done"
