"""The solution loop, its runner and the solution-worker adapter, with a scripted completion: no model, no network."""
from __future__ import annotations

from pathlib import Path

from hubofhubs.the_intelligence.mind.delegation.solution_workers import work_solution
from hubofhubs.the_world.tools.deep import DeepResult
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import CallCounter, build_prompt, unsupported, history_text, parse_reply, run_loop, Outcome
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner, as_solution_worker

FENCE_OPEN, DIVIDER, FENCE_CLOSE = "<" * 7 + " SEARCH", "=" * 7, ">" * 7 + " REPLACE"


def edit(path: str, search: str, replace: str) -> str:
    return f"{path}\n{FENCE_OPEN}\n{search}{DIVIDER}\n{replace}{FENCE_CLOSE}\n"


class Script:
    """A completion that answers from a list of replies (or functions of the prompt) and keeps every prompt it was given."""

    def __init__(self, *replies):
        self.replies, self.prompts, self.systems = list(replies), [], []

    def __call__(self, system, prompt):
        self.systems.append(system)
        self.prompts.append(prompt)
        reply = self.replies.pop(0) if self.replies else "BLOCKED: script ended"
        return reply(prompt) if callable(reply) else reply


def folder(tmp_path: Path, **files: str) -> str:
    for name, text in files.items():
        (tmp_path / name.replace("::", "/")).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name.replace("::", "/")).write_text(text)
    return str(tmp_path)


def test_a_plain_first_answer_from_files_in_view_is_one_call(tmp_path):
    root = folder(tmp_path, **{"facts.txt": "The answer is 42.\n"})
    script = Script("It is 42.")
    got = run_loop("What is the answer in facts.txt?", working_dir=root, complete=script)
    assert got.met and got.report == "It is 42." and got.calls == 1 and got.changed == []
    assert "The answer is 42." in script.prompts[0] and "facts.txt" in got.read


def test_edit_and_passing_check_end_in_one_call(tmp_path):
    root = folder(tmp_path, **{"app.py": "x = 1\n"})
    reply = edit("app.py", "x = 1\n", "x = 2\n") + "CHECK: grep -q 'x = 2' app.py\nREPORT: Set x to 2 in app.py.\n"
    script = Script(reply)
    got = run_loop("Set x to 2", working_dir=root, complete=script)
    assert got.met and got.calls == 1 and got.changed == ["app.py"] and got.report == "Set x to 2 in app.py."
    assert (tmp_path / "app.py").read_text() == "x = 2\n"


def test_a_failing_check_feeds_its_output_to_the_second_call(tmp_path):
    root = folder(tmp_path, **{"app.py": "x = 1\n"})
    first = edit("app.py", "x = 1\n", "x = 2\n") + "CHECK: echo MISSING-THING >&2; exit 1\nREPORT: done\n"
    second = edit("app.py", "x = 2\n", "x = 3\n") + "CHECK: grep -q 'x = 3' app.py\nREPORT: Now x is 3.\n"
    script = Script(first, second)
    got = run_loop("Make x right", working_dir=root, complete=script)
    assert got.met and got.calls == 2 and got.report == "Now x is 3."
    assert "MISSING-THING" in script.prompts[1] and "x = 2" in script.prompts[1] and "x = 1" not in script.prompts[1].split("FILES IN VIEW")[1].split("WHAT HAS")[0]


def test_an_unmatched_search_is_reported_and_the_loop_continues(tmp_path):
    root = folder(tmp_path, **{"app.py": "alpha = 1\nbeta = 2\n"})
    first = edit("app.py", "alpha = 9\nbeta = 2\n", "alpha = 5\nbeta = 2\n") + "REPORT: changed alpha\n"
    second = edit("app.py", "alpha = 1\n", "alpha = 5\n") + "REPORT: alpha is 5\n"
    script = Script(first, second)
    got = run_loop("alpha to 5", working_dir=root, complete=script, review=False)
    assert got.met and got.calls == 2
    assert "FAILED" in script.prompts[1] and "SEARCH text was not found" in script.prompts[1] and "alpha = 1" in script.prompts[1]
    assert "not accepted" in script.prompts[1]


def test_a_new_file_uses_an_empty_search(tmp_path):
    root = folder(tmp_path, **{"keep.txt": "keep\n"})
    script = Script(edit("pkg/new.py", "", "print('hi')\n") + "REPORT: created pkg/new.py\n")
    got = run_loop("create it", working_dir=root, complete=script)
    assert got.met and (tmp_path / "pkg" / "new.py").read_text() == "print('hi')\n" and got.changed == ["pkg/new.py"]


def test_a_path_escaping_the_folder_is_refused(tmp_path):
    inner = tmp_path / "work"
    inner.mkdir()
    script = Script(edit("../outside.txt", "", "bad\n") + "REPORT: wrote it\n", "BLOCKED: cannot")
    got = run_loop("write outside", working_dir=str(inner), complete=script)
    assert not (tmp_path / "outside.txt").exists() and not got.met and got.calls == 2
    assert "outside the working folder" in script.prompts[1]


def test_a_refused_command_is_a_failed_action(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    script = Script("RUN: git push origin main\nREPORT: pushed\n", "BLOCKED: refused")
    got = run_loop("push", working_dir=root, complete=script)
    assert not got.met and got.commands == 0 and "refused" in script.prompts[1] and "not accepted" in script.prompts[1]


def test_read_adds_a_file_to_view(tmp_path):
    root = folder(tmp_path, **{"small.txt": "s\n", "big.txt": "BIGTEXT " * 400})
    script = Script("READ: big.txt\nREAD: nothing.txt\nNOTE: looking", lambda prompt: "REPORT: " + ("saw big" if "BIGTEXT" in prompt else "did not"))
    got = run_loop("look", working_dir=root, complete=script, view_chars=50)
    assert "BIGTEXT" not in script.prompts[0] and "BIGTEXT" in script.prompts[1]
    assert "no such file" in script.prompts[1] and "looking" in script.prompts[1]
    assert got.met and got.report == "saw big" and "big.txt" in got.read


def test_a_report_written_with_a_read_in_the_same_reply_waits_for_the_text(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a" * 20, "b.txt": "SECRETB" + "x" * 200})
    script = Script("READ: b.txt\nREPORT: guess", "REPORT: b says SECRETB")
    got = run_loop("what is in b", working_dir=root, complete=script, view_chars=120)
    assert got.calls == 2 and got.report == "b says SECRETB"


def test_files_named_in_the_goal_come_first_and_a_folder_that_fits_is_all_in_view(tmp_path):
    root = folder(tmp_path, **{"named.txt": "N" * 300, "tiny.txt": "t\n", "medium.txt": "m" * 100, "huge.txt": "h" * 5000})
    script = Script("ok")
    run_loop("Summarise named.txt", working_dir=root, complete=script, view_chars=450)
    view = script.prompts[0].split("FILES IN VIEW")[1].split("WHAT HAS")[0]
    assert "=== named.txt ===" in view and "=== tiny.txt ===" not in view and "=== huge.txt ===" not in view      # too large to fit: only what is named
    assert "huge.txt (5000 bytes)  [not in view" in script.prompts[0]
    script = Script("ok")
    run_loop("Summarise named.txt", working_dir=root, complete=script, view_chars=9000)
    view = script.prompts[0].split("FILES IN VIEW")[1].split("WHAT HAS")[0]
    assert all(f"=== {name} ===" in view for name in ("named.txt", "tiny.txt", "medium.txt", "huge.txt"))


def test_the_map_skips_hidden_cache_and_large_files(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a", ".hidden::x.txt": "x", "__pycache__/c.pyc": "c", "node_modules::m.js": "m", "big.txt": "z" * 250_000})
    (tmp_path / "bin.dat").write_bytes(b"\x00\x01\x02")
    script = Script("ok")
    run_loop("go", working_dir=root, complete=script)
    folder_map = script.prompts[0].split("FOLDER MAP")[1].split("FILES IN VIEW")[0]
    assert "a.txt" in folder_map and "x.txt" not in folder_map and "c.pyc" not in folder_map and "m.js" not in folder_map
    assert "big.txt" not in folder_map and "bin.dat" not in folder_map


def test_old_results_are_clipped_and_the_latest_is_full():
    long = "line\n" * 400
    entries = [{"call": 1, "note": "n1", "outcomes": [Outcome("RUN a", True, long)], "advice": ""},
               {"call": 2, "note": "", "outcomes": [Outcome("RUN b", True, long)], "advice": ""}]
    text = history_text(entries)
    first, second = text.split("Call 2:")
    assert len(first) < 700 and "left out" in first and "NOTE: n1" in first
    assert len(second) > 1500 and "left out" not in second


def test_each_prompt_is_rebuilt_not_appended(tmp_path):
    root = folder(tmp_path, **{"app.py": "x = 1\n"})
    script = Script(edit("app.py", "x = 1\n", "x = 2\n") + "NOTE: edited", "RUN: echo hi\nNOTE: ran", "REPORT: ok")
    run_loop("go", working_dir=root, complete=script)
    assert all(prompt.count("GOAL:") == 1 for prompt in script.prompts)
    assert script.prompts[1].count("=== app.py ===") == 1 and "x = 2" in script.prompts[1]


def test_delegate_runs_a_child_and_shares_the_counter(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    child_goal = "write the part"

    def answer(system, prompt):
        if prompt.startswith(f"GOAL:\n{child_goal}"):
            return edit("part.txt", "", "part\n") + "REPORT: wrote part.txt\n"
        if "met=True" in prompt:
            return "REPORT: the part is done"
        return f"DELEGATE: {child_goal}\nNOTE: delegating"

    counter = CallCounter(5)
    got = run_loop("do all", working_dir=root, complete=answer, counter=counter, review=False)
    assert got.met and got.calls == 3 and counter.used == 3 and "part.txt" in got.changed


def test_a_child_gets_no_delegation_and_the_counter_caps_everyone(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    systems = []

    def answer(system, prompt):
        systems.append(system)
        return "DELEGATE: more\nNOTE: again"

    got = run_loop("spin", working_dir=root, complete=answer, max_calls=4, depth=1)
    assert not got.met and "call limit" in got.error and got.calls <= 4
    assert "DELEGATE" in systems[0] and any("DELEGATE:" not in s for s in systems[1:2])


def test_max_calls_spent_ends_not_met_with_the_last_note(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    script = Script("RUN: echo 1\nNOTE: first", "RUN: echo 2\nNOTE: second")
    got = run_loop("never done", working_dir=root, complete=script, max_calls=2)
    assert not got.met and "call limit" in got.error and got.report == "second" and got.calls == 2 and got.commands == 2


def test_cancel_stops_before_a_call(tmp_path):
    script = Script("ok")
    got = run_loop("x", working_dir=folder(tmp_path, **{"a.txt": "a"}), complete=script, cancel=lambda: True)
    assert not got.met and "cancelled" in got.error and script.prompts == []


def test_blocked_ends_not_met_with_the_reason(tmp_path):
    got = run_loop("x", working_dir=folder(tmp_path, **{"a.txt": "a"}), complete=Script("BLOCKED: no network"))
    assert not got.met and got.error == "blocked: no network"


def test_no_action_is_asked_once_then_ends(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    script = Script("NOTE: thinking", "still nothing here")
    got = run_loop("x", working_dir=root, complete=script)
    assert not got.met and got.calls == 2 and "action protocol" in got.error and "none of the actions" in script.prompts[1]


def test_run_without_check_needs_zero_exit_codes(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    got = run_loop("x", working_dir=root, complete=Script("RUN: exit 2\nREPORT: fine", "RUN: true\nREPORT: fine now"))
    assert got.met and got.calls == 2


def test_report_text_is_not_parsed_for_actions(tmp_path):
    reply = parse_reply("RUN: echo hi\nREPORT: I ran\nRUN: rm -rf build\nEND REPORT\nREAD: a.txt")
    assert [a.kind for a in reply.actions] == ["run", "read"] and reply.report == "I ran\nRUN: rm -rf build"


def test_a_completion_that_raises_ends_not_met(tmp_path):
    def boom(system, prompt):
        raise RuntimeError("model down")
    got = run_loop("x", working_dir=folder(tmp_path, **{"a.txt": "a"}), complete=boom)
    assert not got.met and "model down" in got.error


def test_a_command_that_writes_a_file_is_listed_as_changed(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    got = run_loop("x", working_dir=root, complete=Script("RUN: echo data > made.txt\nREPORT: made it"))
    assert got.met and got.changed == ["made.txt"]


# --- the runner ----------------------------------------------------------------------------------------------------------------------

def runner_for(tmp_path, complete, **kw):
    return SolutionLoopRunner(root=str(tmp_path), complete=complete, model_for=lambda provider, tier: "stub-model", **kw)


def test_the_runner_returns_a_deep_result(tmp_path):
    root = folder(tmp_path, **{"app.py": "x = 1\n"})
    runner = runner_for(tmp_path, Script(edit("app.py", "x = 1\n", "x = 2\n") + "CHECK: grep -q 'x = 2' app.py\nREPORT: x is 2\n"))
    got = runner.run_goal(goal="g", brief="Set x to 2", max_turns=5)
    assert isinstance(got, DeepResult) and got.met and got.output == "x is 2" and got.changes_landed == 1 and not got.changed_nothing
    assert runner.model == "stub-model" and got.resolved_model == "stub-model" and Path(root, "app.py").read_text() == "x = 2\n"


def test_the_runner_uses_the_brief_context_and_standing_instructions(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings
    folder(tmp_path, **{"a.txt": "a"})
    script = Script("ok")
    runner = runner_for(tmp_path, script, settings=GoalSettings(standing_instructions=lambda: "STANDING RULE"))
    runner.run_goal(goal="the goal", brief="the brief", context_preamble="PREAMBLE")
    assert "the brief" in script.prompts[0] and "PREAMBLE" in script.prompts[0] and "STANDING RULE" in script.prompts[0]


def test_the_runner_never_raises_when_the_completion_raises(tmp_path):
    def boom(system, prompt):
        raise RuntimeError("model down")
    folder(tmp_path, **{"a.txt": "a"})
    got = runner_for(tmp_path, boom).run_goal(goal="g", brief="b")
    assert isinstance(got, DeepResult) and not got.met and "model down" in got.error
    assert not runner_for(tmp_path, boom).run_goal(goal="g", brief="b", working_dir="/no/such/folder").met or True


def test_the_runner_stops_on_the_wall_clock_cap(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
    folder(tmp_path, **{"a.txt": "a"})
    runner = SolutionLoopRunner(SubprocessConfig(working_dir=str(tmp_path), timeout_seconds=-1), complete=Script("RUN: true\nNOTE: n"),
                                model_for=lambda provider, tier: "m")
    got = runner.run_goal(goal="g", brief="b")
    assert not got.met and "time limit" in got.error


def test_the_runner_drives_only_anthropic(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        SolutionLoopRunner(root=str(tmp_path), provider="openai", complete=lambda s, p: "")


def test_the_arm_name_resolves():
    from hubofhubs.the_world.tools.delegated_agent_sessions.arm_choice import eligible, harness_class
    assert harness_class("solution_loop_runner") is SolutionLoopRunner
    assert not eligible("solution_loop_runner@provider=anthropic,tier=fast", ["anthropic"])      # on trial: resolved and measured, not handed out


# --- the solution worker -------------------------------------------------------------------------------------------------------------

def test_as_solution_worker_turns_a_brief_into_one_loop(tmp_path):
    folder(tmp_path, **{"a.txt": "a"})
    script = Script("REPORT: part done")
    runner = runner_for(tmp_path, script)
    work = as_solution_worker(runner, str(tmp_path))
    out = work({"solution_id": "s", "name": "Part", "frame": "FRAME TEXT", "milestone": "MILE", "task": "TASK", "handed": "HANDED", "reports": ["child said X"]})
    assert out == "part done" and all(word in script.prompts[0] for word in ("FRAME TEXT", "MILE", "TASK", "HANDED", "child said X"))
    again = as_solution_worker(runner_for(tmp_path, Script("BLOCKED: no")), str(tmp_path))({"task": "t"})
    assert "not finished" in again


def test_the_worker_serves_the_solution_hierarchy(tmp_path):
    folder(tmp_path, **{"a.txt": "a"})
    work = as_solution_worker(runner_for(tmp_path, lambda system, prompt: "REPORT: worked"), str(tmp_path))
    report = work_solution("s1", frame=lambda sid: {"name": "S", "milestone": "m"}, children=lambda sid, task: [], work=work,
                           check=lambda sid, milestone, output: {"met": output == "worked"}, task="t")
    assert report.status == "met" and report.output == "worked"


def test_prompt_builder_keeps_the_parts_in_order():
    text = build_prompt("G", "C", "MAP", "FILES", [], "")
    assert text.index("GOAL") < text.index("CONTEXT") < text.index("FOLDER MAP") < text.index("FILES IN VIEW") < text.index("WHAT HAS HAPPENED")


def test_written_text_with_an_unsupported_figure_gets_one_review_that_can_correct_it(tmp_path):
    root = folder(tmp_path, **{"facts.txt": "Sales were 12 units.\n"})
    script = Script(edit("out.md", "", "Sales were 99 units.\n") + "REPORT: wrote out.md",
                    edit("out.md", "Sales were 99 units.\n", "Sales were 12 units.\n") + edit("facts.txt", "Sales were 12 units.\n", "x\n"))
    got = run_loop("Write out.md with the sales figure from facts.txt.", working_dir=root, complete=script)
    assert got.met and got.calls == 2 and got.report == "wrote out.md"
    assert (tmp_path / "out.md").read_text() == "Sales were 12 units.\n"
    assert (tmp_path / "facts.txt").read_text() == "Sales were 12 units.\n"      # a reviewer corrects the work, never the sources
    assert "You review finished work" in script.systems[1] and "wrote out.md" not in script.prompts[1]
    assert "out.md: the figure 99 is in no source file" in script.prompts[1]


def test_supported_text_and_code_are_accepted_with_no_review_call(tmp_path):
    root = folder(tmp_path, **{"facts.txt": "Sales were 12 units.\n"})
    script = Script(edit("b.md", "", "Sales were 12 units (facts.txt).\n") + "REPORT: done")
    got = run_loop("Write b.md.", working_dir=root, complete=script)
    assert got.met and got.calls == 1
    code = Script(edit("c.py", "", "x = 4321\n") + "REPORT: done")
    got = run_loop("Write c.py.", working_dir=root, complete=code)
    assert got.met and got.calls == 1
    off = Script(edit("d.md", "", "Sales were 77 units.\n") + "REPORT: done")
    got = run_loop("Write d.md.", working_dir=root, complete=off, review=False)
    assert got.met and got.calls == 1


def test_files_not_in_view_are_marked_in_the_map(tmp_path):
    root = folder(tmp_path, **{"small.txt": "s\n", "big.txt": "b" * 500})
    script = Script("It is s.")
    run_loop("What is in the small file?", working_dir=root, complete=script, view_chars=100)
    assert "big.txt (500 bytes)  [not in view" in script.prompts[0] and "small.txt (2 bytes)\n" in script.prompts[0]


def test_the_code_check_lists_figures_and_files_the_sources_do_not_hold(tmp_path):
    root = folder(tmp_path, **{"notes.txt": "Trips rose 18 percent to 2,360 in 2025.\n",
                               "out.md": "Trips rose 18 percent to 2360 (notes.txt). Revenue was 4,400 (ledger.csv). Step 3.\n"})
    assert unsupported(root, ["out.md"]) == ["out.md: the figure 4400 is in no source file", "out.md: names the file ledger.csv, which is not in the folder"]
    assert unsupported(root, ["code.py"]) == []
    script = Script(edit("new.md", "", "Revenue was 7,700.\n") + "REPORT: done", "OK")
    run_loop("Write new.md.", working_dir=root, complete=script)
    assert "new.md: the figure 7700 is in no source file" in script.prompts[1]


def test_a_folder_larger_than_the_view_shows_only_what_the_goal_points_at(tmp_path):
    files = {f"misc{n}.txt": "filler text\n" * 3 for n in range(30)}
    files["budget_notes.txt"] = "The venue costs 300.\n" * 5
    root = folder(tmp_path, **files)
    script = Script("It is 300.")
    run_loop("What does the venue cost according to the budget?", working_dir=root, complete=script, view_chars=400)
    view = script.prompts[0].split("FILES IN VIEW (current):")[1].split("WHAT HAS HAPPENED")[0]
    assert "=== budget_notes.txt ===" in view and "=== misc" not in view


def test_a_harness_on_trial_is_ranked_but_never_chosen_for_a_consumer():
    from hubofhubs.the_world.tools.delegated_agent_sessions import arm_choice
    assert SolutionLoopRunner.on_trial and not arm_choice.eligible("solution_loop_runner@provider=anthropic,tier=fast", ["anthropic"])
    assert arm_choice.eligible("subprocess_goal_runner@provider=anthropic,tier=fast", ["anthropic"])


def test_an_escalation_marker_in_the_report_is_a_decision_not_a_met_run(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings
    root = folder(tmp_path, **{"a.txt": "one\n"})
    runner = SolutionLoopRunner(complete=Script("REPORT: I need a person for this.\nRAISED: dec_123abc"), root=root,
                                settings=GoalSettings(escalation_marker="RAISED:"))
    got = runner.run_goal(goal="Decide the budget.", brief="", working_dir=root)
    assert got.met is False and got.decision_id == "dec_123abc"


# --- resume, steering, tools, sandbox --------------------------------------------------------------------------------------------------

import json
import os
import shutil
import tempfile
import threading

import pytest

from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import LoopState, Tool


def keeper(root, sessions, complete, **kw):
    return SolutionLoopRunner(root=str(root), complete=complete, model_for=lambda provider, tier: "stub-model", session_dir=str(sessions), **kw)


def test_loop_state_round_trips_through_json():
    state = LoopState(goal="g", entries=[{"call": 1, "note": "n", "advice": "a", "reply": "x", "outcomes": [Outcome("RUN x", True, "exit 0")]},
                                         {"message": "hello"}], view=[("a.txt", True), ("b.txt", False)], changed=["a.txt"], read=["a.txt", "b.txt"], calls=3)
    back = LoopState.from_json(state.to_json())
    assert back.goal == "g" and back.view == [("a.txt", True), ("b.txt", False)] and back.calls == 3 and back.changed == ["a.txt"]
    assert back.entries[0]["outcomes"][0] == Outcome("RUN x", True, "exit 0") and back.entries[0]["advice"] == "a" and back.entries[1] == {"message": "hello"}
    assert "reply" not in json.loads(state.to_json())["entries"][0]
    with pytest.raises(ValueError):
        LoopState.from_json("not json")


def test_save_is_called_after_every_call(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    saved = []
    script = Script("RUN: echo one\nNOTE: first", "RUN: echo two\nNOTE: second", "REPORT: done")
    got = run_loop("go", working_dir=root, complete=script, save=lambda state: saved.append(state.calls))
    assert got.met and saved == [1, 2, 3]


def test_a_second_run_continues_the_history_and_the_view(tmp_path):
    work, sessions = tmp_path / "work", tmp_path / "sessions"
    work.mkdir()
    folder(work, **{"a.txt": "ALPHA\n", "b.txt": "BETA\n"})
    first = Script("READ: b.txt\nRUN: echo first-run-output\nNOTE: step one", "RUN: echo again\nNOTE: step two")
    runner = keeper(work, sessions, first)
    one = runner.run_goal(goal="check a.txt", run_id="s1", max_turns=2)
    assert not one.met and one.session_id == "s1" and (sessions / "s1.json").exists()
    second = Script("REPORT: carried on")
    two = keeper(work, sessions, second).run_goal(goal="check a.txt again with b.txt", resume_session_id="s1", max_turns=2)
    assert two.met and two.session_id == "s1"
    prompt = second.prompts[0]
    assert "first-run-output" in prompt and "step one" in prompt and "=== b.txt ===" in prompt
    assert "EARLIER GOAL:\ncheck a.txt" in prompt and prompt.startswith("GOAL:\ncheck a.txt again with b.txt")
    assert "Call 3:" not in prompt and "Call 2:" in prompt


def test_the_same_goal_shows_no_earlier_goal(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    state = LoopState(goal="same", entries=[], view=[("a.txt", False)])
    script = Script("REPORT: ok")
    run_loop("same", working_dir=root, complete=script, state=state)
    assert "EARLIER GOAL" not in script.prompts[0]


def test_a_corrupt_session_file_starts_fresh(tmp_path):
    work, sessions = tmp_path / "work", tmp_path / "sessions"
    work.mkdir()
    sessions.mkdir()
    (sessions / "bad.json").write_text("{ this is not json")
    script = Script("The answer.")
    got = keeper(work, sessions, script).run_goal(goal="question", resume_session_id="bad")
    assert got.met and got.session_id == "bad" and "Nothing yet" in script.prompts[0]


def test_a_message_in_the_inbox_reaches_the_next_prompt_and_is_kept_clipped(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    waiting = []
    script = Script(lambda prompt: (waiting.append("Use the blue one instead") or "RUN: echo one\nNOTE: first"), "RUN: echo two\nNOTE: second", "REPORT: done")

    def inbox():
        got, waiting[:] = list(waiting), []
        return got

    got = run_loop("go", working_dir=root, complete=script, inbox=inbox)
    line = "MESSAGE FROM THE PERSON (follow it; it overrides the plan so far): Use the blue one instead"
    assert "MESSAGE" not in script.prompts[0] and line in script.prompts[1] and line in script.prompts[2] and got.met


def test_a_report_is_not_accepted_while_an_unseen_message_arrived(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    arrivals = [[], ["Also mention the date"], []]
    script = Script("REPORT: done", "REPORT: done with the date")
    got = run_loop("go", working_dir=root, complete=script, inbox=lambda: arrivals.pop(0) if arrivals else [])
    assert got.calls == 2 and got.report == "done with the date"
    assert "Also mention the date" in script.prompts[1] and "not accepted" in script.prompts[1]


def test_steer_is_false_with_nothing_running_and_true_during_a_run(tmp_path):
    work, sessions = tmp_path / "work", tmp_path / "sessions"
    work.mkdir()
    started, release = threading.Event(), threading.Event()
    prompts = []

    def complete(system, prompt):
        prompts.append(prompt)
        if len(prompts) == 1:
            started.set()
            assert release.wait(10)
            return "RUN: echo one\nNOTE: first"
        return "REPORT: answered"

    runner = keeper(work, sessions, complete)
    assert runner.steer("anyone there?") is False
    done = []
    thread = threading.Thread(target=lambda: done.append(runner.run_goal(goal="g", run_id="r1")))
    thread.start()
    assert started.wait(10)
    assert runner.steer("switch to plan B") is True and runner.steer("x", run_id="other") is False and runner.steer("y", run_id="r1") is True
    release.set()
    thread.join(10)
    assert done[0].met and "switch to plan B" in prompts[1] and runner.steer("late") is False


def test_a_tool_is_listed_called_and_its_result_is_in_the_next_prompt(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    calls = []
    tools = {"search": Tool("look a thing up on the web", lambda text: calls.append(text) or "FOUND-IT: " + text)}
    script = Script("USE: search blue whales\nREPORT: guess", "REPORT: whales are blue")
    got = run_loop("go", working_dir=root, complete=script, tools=tools)
    assert "USE: search <input>   look a thing up on the web" in script.systems[0]
    assert calls == ["blue whales"] and "FOUND-IT: blue whales" in script.prompts[1]
    assert got.met and got.calls == 2 and got.report == "whales are blue"


def test_without_tools_a_use_line_is_not_an_action(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})
    script = Script("USE: search x\nNOTE: n", "REPORT: ok")
    run_loop("go", working_dir=root, complete=script)
    assert "USE: search" not in script.systems[0] and "no tool" not in script.prompts[1]


def test_an_unknown_tool_or_a_failing_tool_fails_the_action(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a\n"})

    def broken(text):
        raise RuntimeError("boom")

    tools = {"search": Tool("find", lambda text: "x"), "broken": Tool("fails", broken)}
    script = Script("USE: nothere hello\nUSE: broken z\nNOTE: try", "REPORT: ok")
    got = run_loop("go", working_dir=root, complete=script, tools=tools)
    assert "there is no tool named 'nothere'" in script.prompts[1] and "RuntimeError: boom" in script.prompts[1] and "FAILED" in script.prompts[1]
    assert got.calls == 2


def test_the_runner_hands_its_tools_to_the_loop(tmp_path):
    work, sessions = tmp_path / "work", tmp_path / "sessions"
    work.mkdir()
    script = Script("USE: ping 1\nREPORT: early", "REPORT: pong seen")
    got = keeper(work, sessions, script, tools={"ping": Tool("pings", lambda text: "pong " + text)}).run_goal(goal="g")
    assert got.met and "pong 1" in script.prompts[1]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not installed")
def test_the_runner_runs_commands_in_the_sandbox(tmp_path):
    work, sessions = tmp_path / "work", tmp_path / "sessions"
    work.mkdir()
    outside = tempfile.mkdtemp()
    try:
        script = Script(f"RUN: echo in > inside.txt\nRUN: echo out > {outside}/out.txt\nRUN: cat /etc/hostname\nNOTE: tried", "REPORT: done")
        keeper(work, sessions, script).run_goal(goal="g")
        assert (work / "inside.txt").read_text() == "in\n" and not (os.path.exists(f"{outside}/out.txt"))
        assert "RUN echo out" in script.prompts[1] and "FAILED" in script.prompts[1]
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_a_figure_worked_out_from_two_source_figures_is_not_listed(tmp_path):
    root = folder(tmp_path, **{"limit.txt": "Keep it under 9,000 words.\n", "count.txt": "It is at 7,950 words.\n",
                               "out.md": "There is room for 1,050 words (9,000 less 7,950). We need 3,333 more readers.\n"})
    assert unsupported(root, ["out.md"]) == ["out.md: the figure 3333 is in no source file"]
