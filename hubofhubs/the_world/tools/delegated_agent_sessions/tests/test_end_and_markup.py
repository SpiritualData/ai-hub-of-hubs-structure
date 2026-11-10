"""Function-call markup is read as the actions it means, every end of a loop has a reason, a cap does not end a run that is working, a follow-up resumes, and
a model that runs one command per reply is asked to batch. Scripted completion, no model."""
import threading
import time

from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import Tool, parse_reply, read_only, run_loop, Action
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner

FENCE = "`" * 3
SEARCH, DIVIDER, REPLACE = "<" * 7 + " SEARCH", "=" * 7, ">" * 7 + " REPLACE"


class Script:
    def __init__(self, *replies):
        self.replies, self.prompts, self.systems = list(replies), [], []

    def __call__(self, system, prompt):
        self.systems.append(system)
        self.prompts.append(prompt)
        return self.replies.pop(0) if self.replies else "BLOCKED: script ended"


def kinds(reply):
    return [(a.kind, a.text) for a in reply.actions]


# --- 1. markup ----------------------------------------------------------------------------------------------------------------------------

def test_invoke_blocks_are_the_actions_they_name_with_or_without_the_wrapper():
    one = parse_reply('<invoke name="RUN">\n<parameter name="command">echo a</parameter>\n</invoke>')
    two = parse_reply('<function_calls>\n<invoke name="READ"><parameter name="path">a.txt</parameter></invoke>\n<invoke name="CHECK"><parameter name="command">test -f a.txt</parameter></invoke>\n</function_calls>')
    assert kinds(one) == [("run", "echo a")] and kinds(two) == [("read", "a.txt"), ("check", "test -f a.txt")]
    assert parse_reply('<invoke name="DELEGATE"><parameter name="task">write the tests</parameter></invoke>').actions[0].kind == "delegate"
    use = parse_reply('<invoke name="USE"><parameter name="name">search</parameter><parameter name="input">weekly run</parameter></invoke>', tools=True)
    assert kinds(use) == [("use", "search weekly run")]


def test_the_reply_from_the_real_task_a_stray_parameter_is_a_run_and_state_still_parses():
    text = ('<invoke name="RUN">\n<parameter name="command">printf \'%s\\n\' \'import json\' > /tmp/s/f.py</parameter>\n</invoke>\n'
            '<parameter name="command">~/hq/hqenv/bin/python3 -I /tmp/s/f.py | head -80</parameter>\n</invoke>\nSTATE: done: wrote the script\n')
    reply = parse_reply(text)
    assert [a.kind for a in reply.actions] == ["run", "run"] and reply.actions[1].text.endswith("| head -80") and reply.state == "done: wrote the script" and not reply.unmapped


def test_a_multi_line_parameter_body_is_one_command():
    reply = parse_reply('<invoke name="RUN"><parameter name="command">set -e\ncd sub\npython3 - <<\'EOF\'\nprint(1)\nEOF</parameter></invoke>')
    assert len(reply.actions) == 1 and reply.actions[0].text.count("\n") == 4 and reply.actions[0].text.startswith("set -e")


def test_a_json_action_on_a_line_or_in_a_fenced_block_is_an_action():
    reply = parse_reply(f'{{"action": "RUN", "command": "ls -la"}}\n{FENCE}json\n[{{"action": "READ", "path": "a.txt"}}, {{"action": "CHECK", "command": "true"}}]\n{FENCE}\n')
    assert kinds(reply) == [("run", "ls -la"), ("read", "a.txt"), ("check", "true")]


def test_markup_inside_a_report_or_an_edit_block_is_not_run():
    inside_report = parse_reply('RUN: echo real\nREPORT: I tried <invoke name="RUN"><parameter name="command">rm -rf x</parameter></invoke> earlier.\n')
    assert kinds(inside_report) == [("run", "echo real")] and "rm -rf x" in inside_report.report
    edit = f'notes.md\n{SEARCH}\n{DIVIDER}\n<invoke name="RUN"><parameter name="command">rm -rf x</parameter></invoke>\n{REPLACE}\n'
    assert [a.kind for a in parse_reply(edit).actions] == ["edit"]


def test_markup_that_names_no_action_is_quoted_in_what_the_loop_tells_the_model_and_in_the_end_reason(tmp_path):
    odd = '<invoke name="Frobnicate"><parameter name="x">' + "y" * 200 + "</parameter></invoke>"
    script = Script(odd, odd)
    got = run_loop("Work", working_dir=str(tmp_path), complete=script, review=False)
    assert got.ended == "no_action" and "names no action" in got.error and "Frobnicate" in got.error
    assert "could not be mapped to an action" in script.prompts[1] and "Frobnicate" in script.prompts[1] and "none of the actions" not in script.prompts[1]
    assert len(parse_reply(odd).unmapped) <= 120


def test_a_reply_written_in_markup_does_the_work(tmp_path):
    reply = '<function_calls>\n<invoke name="RUN"><parameter name="command">echo made > made.txt</parameter></invoke>\n</function_calls>\nREPORT: ok\n'
    got = run_loop("Make it", working_dir=str(tmp_path), complete=Script(reply), review=False)
    assert got.met and (tmp_path / "made.txt").read_text() == "made\n"


def test_the_system_text_says_the_markup_is_not_needed(tmp_path):
    script = Script("It is fine.")
    run_loop("Say", working_dir=str(tmp_path), complete=script)
    assert "function-call markup" in script.systems[0] and "not needed" in script.systems[0]


# --- 2. why a loop ended -------------------------------------------------------------------------------------------------------------------

def test_every_end_has_a_reason(tmp_path):
    work = str(tmp_path)
    assert run_loop("a", working_dir=work, complete=Script("It is fine."), review=False).ended == "met"
    assert run_loop("a", working_dir=work, complete=Script("RUN: echo x\nREPORT: ok\n"), review=False).ended == "met"
    assert run_loop("a", working_dir=work, complete=Script("BLOCKED: no access"), review=False).ended == "blocked"
    assert run_loop("a", working_dir=work, complete=Script("RUN: echo x\n", "hm", "hmm"), review=False).ended == "no_action"
    assert run_loop("a", working_dir=work, complete=Script(*["RUN: echo x\n"] * 3), review=False, max_calls=2).ended == "call_limit"
    assert run_loop("a", working_dir=work, complete=Script("RUN: echo x\n"), review=False, cancel=lambda: True).ended == "cancelled"
    check = "CHECK: echo no >&2; exit 1\nREPORT: needs a person\n"
    assert run_loop("a", working_dir=work, complete=Script(check, check), review=False).ended == "partial"

    def broken(system, prompt):
        raise RuntimeError("service down")
    assert run_loop("a", working_dir=work, complete=broken, review=False).ended == "model_failed"


def runner_in(tmp_path, complete, **kw):
    return SolutionLoopRunner(root=str(tmp_path), complete=complete, sandbox=False, review=False, session_dir=str(tmp_path / "s"), model_for=lambda p, t: "m", **kw)


def test_the_consumers_turn_limit_is_the_call_limit_of_one_loop_and_the_result_says_so(tmp_path):
    deep = runner_in(tmp_path, Script(*["RUN: echo x\n"] * 9)).run_goal(goal="Work", max_turns=3, run_id="r1")
    assert deep.end_reason == "call_limit" and deep.limit_hit and not deep.met


def test_a_wall_clock_cap_waits_for_the_call_in_flight_and_ends_the_loop_between_calls_as_a_time_limit(tmp_path):
    seen = []

    def slow(system, prompt):
        seen.append(prompt)
        time.sleep(0.4)
        return "RUN: echo kept > kept.txt\nSTATE: learned: step one done\n"
    runner = runner_in(tmp_path, slow)
    runner.cfg.timeout_seconds = 0.1
    deep = runner.run_goal(goal="Work", run_id="r2", max_turns=10)
    assert len(seen) == 1 and (tmp_path / "kept.txt").exists()          # the call was not abandoned by the cap; its work was done
    assert deep.end_reason == "time_limit" and deep.limit_hit and not deep.met and deep.session_id == "r2"


def test_a_follow_up_with_the_same_run_id_resumes_with_state_and_history_and_a_met_one_does_not(tmp_path):
    first = Script("RUN: echo one\nSTATE: learned: the code is 4417\n", "RUN: echo two\n")
    runner_in(tmp_path, first).run_goal(goal="Work", run_id="r3", max_turns=2)
    second = Script("REPORT: ok\n")
    deep = runner_in(tmp_path, second).run_goal(goal="Work again, with what was missing", run_id="r3", max_turns=2)
    assert deep.met and "the code is 4417" in second.prompts[0] and "echo two" in second.prompts[0] and "EARLIER GOAL:\nWork" in second.prompts[0]
    third = Script("It is done.")
    runner_in(tmp_path, third).run_goal(goal="A new task", run_id="r3")
    assert "YOUR STATE" not in third.prompts[0] and "EARLIER GOAL" not in third.prompts[0]


def test_an_explicit_resume_session_id_continues_where_it_was(tmp_path):
    runner_in(tmp_path, Script("RUN: echo one\nSTATE: learned: S-42\n")).run_goal(goal="Work", run_id="r4", max_turns=1)
    script = Script("REPORT: ok\n")
    runner_in(tmp_path, script).run_goal(goal="Work", run_id="r5", resume_session_id="r4")
    assert "S-42" in script.prompts[0]


def test_the_run_totals_line_carries_the_end_reason(tmp_path, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="hubofhubs.deep"):
        runner_in(tmp_path, Script("It is fine.")).work("Say", run_id="r6", session_id="r6")
    assert any(r.getMessage().endswith("ended: met") for r in caplog.records)


# --- 3. fewer, fuller calls ---------------------------------------------------------------------------------------------------------------

def test_one_read_only_command_per_reply_three_times_in_a_row_gets_a_reminder_to_batch(tmp_path):
    script = Script("RUN: ls\n", "RUN: cat a.txt\n", "RUN: head -3 a.txt\n", "RUN: grep x a.txt\n", "REPORT: ok\n")
    (tmp_path / "a.txt").write_text("x\n")
    run_loop("Look", working_dir=str(tmp_path), complete=script, review=False)
    assert "per reply 3 times in a row" not in script.prompts[2] and "per reply 3 times in a row" in script.prompts[3] and "heredoc" in script.prompts[3]


def test_a_reply_that_does_more_resets_the_count_and_the_state_header_says_how_many_calls_remain(tmp_path):
    script = Script("RUN: ls\nSTATE: s", "RUN: cat a.txt\n", "RUN: echo x > b.txt\n", "RUN: ls\n", "RUN: ls\n", "REPORT: ok\n")
    (tmp_path / "a.txt").write_text("x\n")
    run_loop("Look", working_dir=str(tmp_path), complete=script, review=False, max_calls=8)
    assert all("per reply 3 times in a row" not in p for p in script.prompts)
    assert "; 6 calls remain):" in script.prompts[1] and "; 5 calls remain):" in script.prompts[2]


def test_what_counts_as_only_looking():
    assert read_only(Action("run", "ls -la")) and read_only(Action("read", "a.txt")) and read_only(Action("run", "grep -n x a.txt"))
    assert not read_only(Action("run", "echo x > a.txt")) and not read_only(Action("run", "sed -i s/a/b/ f")) and not read_only(Action("run", "python3 build.py"))
    assert not read_only(Action("run", "ls\nrm x"))
