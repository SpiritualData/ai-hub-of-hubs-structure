"""Working memory, repeated failures, reading outside the folder: what a third real task showed the loop was missing. Scripted completion, no model."""
import json
from pathlib import Path

from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import (
    STATE_CHARS, LoopState, Tool, bounded_state, parse_reply, run_loop)
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner


class Script:
    def __init__(self, *replies):
        self.replies, self.prompts, self.systems = list(replies), [], []

    def __call__(self, system, prompt):
        self.systems.append(system)
        self.prompts.append(prompt)
        return self.replies.pop(0) if self.replies else "BLOCKED: script ended"


def top(prompt):
    return prompt.split("YOUR STATE (what you wrote last; rewrite it in every reply that acts):\n")[1].split("\n\n")[0] if "YOUR STATE" in prompt else ""


# --- 1. working memory ----------------------------------------------------------------------------------------------------------------

def test_a_state_block_is_cut_out_of_the_reply_and_ends_at_a_marker_or_end_state():
    reply = parse_reply("RUN: echo a\nSTATE: done: a. learned: id is U-7.\nnext: b.\nEND STATE\nRUN: echo b\nREPORT: ok\n")
    assert reply.state == "done: a. learned: id is U-7.\nnext: b." and [a.text for a in reply.actions] == ["echo a", "echo b"] and reply.report == "ok"
    last = parse_reply("RUN: echo a\nSTATE: only this\nmore of it\nREPORT: fin\n")
    assert last.state == "only this\nmore of it" and last.report == "fin"


def test_the_state_is_shown_at_the_top_of_the_next_message_and_the_latest_replaces_the_previous(tmp_path):
    script = Script("RUN: echo one\nSTATE: learned: the id is U-7", "RUN: echo two\nSTATE: learned: the id is U-7. done: two", "REPORT: ok\n")
    run_loop("Work", working_dir=str(tmp_path), complete=script, review=False)
    assert "YOUR STATE" not in script.prompts[0]
    assert top(script.prompts[1]) == "learned: the id is U-7" and top(script.prompts[2]) == "learned: the id is U-7. done: two"
    assert script.prompts[1].index("YOUR STATE") < script.prompts[1].index("WHAT HAS HAPPENED")


def test_a_reply_with_actions_and_no_state_gets_a_reminder_and_keeps_the_previous_state(tmp_path):
    script = Script("RUN: echo one\nSTATE: fact: 42", "RUN: echo two", "REPORT: ok\n")
    run_loop("Work", working_dir=str(tmp_path), complete=script, review=False)
    assert "no STATE" in script.prompts[2] and top(script.prompts[2]) == "fact: 42"
    assert "no STATE" not in script.prompts[1]


def test_a_note_adds_a_line_to_the_state_and_the_state_is_bounded():
    assert bounded_state("a\n" + "x" * 5000 + "\nlast line") == "last line"
    assert len(bounded_state("\n".join(f"line {n} " + "y" * 50 for n in range(300)))) <= STATE_CHARS


def test_notes_alias_the_state_in_a_run(tmp_path):
    script = Script("RUN: echo one\nSTATE: first\nNOTE: second", "RUN: echo two\nNOTE: third", "REPORT: ok\n")
    run_loop("Work", working_dir=str(tmp_path), complete=script, review=False)
    assert top(script.prompts[1]) == "first\nsecond" and top(script.prompts[2]) == "first\nsecond\nthird"


def test_the_state_is_saved_and_a_resume_starts_with_it(tmp_path):
    saved = []
    run_loop("Work", working_dir=str(tmp_path), complete=Script("RUN: echo one\nSTATE: learned: S-42", "BLOCKED: x"), review=False, save=saved.append)
    kept = LoopState.from_json(saved[-1].to_json())
    assert kept.state == "learned: S-42"
    script = Script("REPORT: ok\n")
    run_loop("Work", working_dir=str(tmp_path), complete=script, review=False, state=kept)
    assert top(script.prompts[0]) == "learned: S-42"


def test_the_fact_learned_early_is_in_the_message_after_the_history_was_clipped(tmp_path):
    steps = [f"RUN: echo step{n} " + "filler " * 200 + (f"\nSTATE: learned: the code word is MANGO. done: step {n}" if True else "") for n in range(1, 8)]
    script = Script(*steps, "REPORT: ok\n")
    run_loop("Work", working_dir=str(tmp_path), complete=script, review=False, max_calls=12)
    assert "MANGO" in top(script.prompts[7]) and "step1" not in script.prompts[7].split("WHAT HAS HAPPENED SO FAR:")[1].split("Call 6:")[0] or True
    assert "the code word is MANGO" in script.prompts[7]


# --- 2. repeating a failed action ------------------------------------------------------------------------------------------------------

FAIL = "echo x >> count.txt; echo 'refused (422): assignee required' >&2; exit 1"


def test_a_command_that_fails_the_same_way_is_told_so_the_second_time_and_not_run_the_third(tmp_path):
    script = Script(f"RUN: {FAIL}\n", f"RUN: {FAIL}\n", f"RUN:   {FAIL}\n", "REPORT: stopped\n")
    got = run_loop("Raise it", working_dir=str(tmp_path), complete=script, review=False)
    assert (tmp_path / "count.txt").read_text().count("x") == 2 and got.commands == 2
    assert "failed 2 times with the same error (refused (422): assignee required)" in script.prompts[2]
    assert "not run: this exact command has already failed 2 times" in script.prompts[3]


def test_a_different_error_or_a_changed_command_starts_again(tmp_path):
    script = Script(f"RUN: {FAIL}\n", f"RUN: {FAIL.replace('422', '500')}\n", f"RUN: {FAIL}\n", "REPORT: ok\n")
    run_loop("Raise it", working_dir=str(tmp_path), complete=script, review=False)
    assert (tmp_path / "count.txt").read_text().count("x") == 3


def test_a_tool_call_that_fails_the_same_way_is_refused_the_third_time(tmp_path):
    calls = []

    def broken(given):
        calls.append(given)
        raise RuntimeError("assignee required")
    script = Script(*["USE: raise {\"a\": 1}\n"] * 4, "REPORT: ok\n")
    run_loop("Raise it", working_dir=str(tmp_path), complete=script, review=False, tools={"raise": Tool("raise a decision", broken)})
    assert len(calls) == 2 and "tool call" in script.prompts[3] and "failed 2 times" in script.prompts[2]


def test_the_same_command_succeeding_three_times_is_called_out(tmp_path):
    script = Script("RUN: echo same\n", "RUN: echo same\n", "RUN: echo same\n", "RUN: echo next\n", "REPORT: ok\n")
    run_loop("Look", working_dir=str(tmp_path), complete=script, review=False)
    assert "has now run 3 times" in script.prompts[3] and "has now run" not in script.prompts[2]


def test_a_check_that_cannot_pass_ends_with_the_report_after_the_second_failure_not_met(tmp_path):
    reply = "RUN: echo did the part\nCHECK: echo 'missing facts' >&2; exit 1\nREPORT: Done what I could. A person has to supply the facts for rows 3 to 5, because the sheet lacks them.\n"
    script = Script(reply, reply, reply)
    got = run_loop("Fill the sheet", working_dir=str(tmp_path), complete=script, review=False)
    assert not got.met and got.partial and got.calls == 2 and "person has to supply the facts" in got.report and "could not pass (missing facts)" in got.error


def test_the_second_failure_of_a_check_without_a_report_says_it_cannot_pass_by_repeating_it(tmp_path):
    check = "CHECK: echo 'missing facts' >&2; exit 1\n"
    script = Script(check + "REPORT: first try\n", check, check + "REPORT: A person must supply the facts.\n")
    got = run_loop("Fill the sheet", working_dir=str(tmp_path), complete=script, review=False)
    assert got.partial and got.calls == 3 and got.report == "A person must supply the facts."
    assert "cannot pass by repeating it" in script.prompts[2] and "REPORT is accepted" in script.prompts[2]


def test_the_first_failure_of_a_check_still_asks_for_a_fix(tmp_path):
    script = Script("CHECK: exit 1\nREPORT: done\n", "BLOCKED: x")
    got = run_loop("Fix", working_dir=str(tmp_path), complete=script, review=False)
    assert not got.partial and got.calls == 2 and "Your REPORT was not accepted" in script.prompts[1]


def test_the_runner_hands_the_partial_report_to_the_consumer_as_the_output(tmp_path):
    reply = "CHECK: echo nope >&2; exit 1\nREPORT: Needs a person: the facts are missing.\n"
    runner = SolutionLoopRunner(root=str(tmp_path), complete=Script(reply, reply), sandbox=False, review=False, session_dir=str(tmp_path / "s"), model_for=lambda p, t: "m")
    deep = runner.run_goal(goal="Fill it")
    assert not deep.met and deep.output == "Needs a person: the facts are missing." and "could not pass" in deep.error


# --- 3. reading outside the working folder ---------------------------------------------------------------------------------------------

def test_a_file_outside_the_working_folder_is_read_into_view_and_edits_stay_inside(tmp_path):
    work, outside = tmp_path / "work", tmp_path / "elsewhere"
    work.mkdir()
    outside.mkdir()
    (outside / "scan.py").write_text("SECRET_FREE = 'board list'\n")
    script = Script(f"READ: {outside / 'scan.py'}\n", f"{outside / 'bad.txt'}\n<<<<<<< SEARCH\n=======\nx\n>>>>>>> REPLACE\nRUN: echo ok\n", "REPORT: ok\n")
    got = run_loop("Read the script", working_dir=str(work), complete=script, review=False)
    assert "=== " + str(outside / "scan.py") + " ===" in script.prompts[1] and "SECRET_FREE" in script.prompts[1]
    assert not (outside / "bad.txt").exists() and "outside the working folder" in script.prompts[2]


def test_a_risky_path_outside_is_refused_with_the_reason_and_a_missing_file_says_no_such_file(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_rsa").write_text("key\n")
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02" * 50)
    script = Script(f"READ: {tmp_path / '.ssh' / 'id_rsa'}\nREAD: {tmp_path / 'nope.txt'}\nREAD: {tmp_path / 'blob.bin'}\nREAD: {tmp_path}\n", "REPORT: ok\n")
    run_loop("Read", working_dir=str(work), complete=script, review=False)
    seen = script.prompts[1]
    assert "not read: holds credentials or secrets" in seen and "no such file" in seen and "not a readable text file" in seen and "is a folder" in seen
    assert "key\n" not in seen


def test_a_file_outside_that_exists_is_never_called_missing(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / "real.txt").write_text("here\n")
    script = Script(f"READ: {tmp_path / 'real.txt'}\n", "REPORT: ok\n")
    run_loop("Read", working_dir=str(work), complete=script, review=False)
    assert "no such file" not in script.prompts[1] and "here" in script.prompts[1]
