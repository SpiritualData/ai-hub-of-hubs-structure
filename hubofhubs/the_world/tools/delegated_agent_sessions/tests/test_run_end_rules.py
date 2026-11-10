"""How a loop run may end met: only on an explicit REPORT that passes the acceptance rules. A reply that mixes markup with the protocol is parsed as the one
command it is, a REPORT whose STATE still lists next steps is not accepted, and a run that ends not met returns its last note or its STATE, never raw action
markup. Scripted completion, no model."""
from pathlib import Path

from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import next_steps, parse_reply, reads_as_work, run_loop, says_actions


class Script:
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, system, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0) if self.replies else "BLOCKED: script ended"


# The shape a real lane task wrote: an invoke wrapper with no parameter whose body is a protocol RUN with a heredoc, a stray closing parameter tag, then a STATE.
MIXED = ('<invoke name="RUN">\nRUN: mkdir -p /tmp/work && cat > /tmp/work/e1.py <<\'EOF\'\nprint("one")\nEOF\n</parameter>\n</invoke>\n'
         'STATE: done: nothing written. next: read /tmp/work/e1.out\nEND STATE\n')


def test_markup_that_wraps_protocol_lines_is_that_one_command_with_the_stray_tags_dropped():
    reply = parse_reply(MIXED)
    runs = [a for a in reply.actions if a.kind == "run"]
    assert len(runs) == 1 and not reply.unmapped
    assert runs[0].text.startswith("mkdir -p /tmp/work && cat > /tmp/work/e1.py <<'EOF'") and runs[0].text.rstrip().endswith("EOF")
    assert "</parameter>" not in runs[0].text and "<invoke" not in runs[0].text
    assert reply.state.startswith("done: nothing written")


def test_the_wrapped_command_runs_in_a_loop(tmp_path):
    reply = ('<invoke name="RUN">\nRUN: echo wrapped > w.txt\n</parameter>\n</invoke>\n')
    script = Script(reply, "REPORT: wrote w.txt\n")
    got = run_loop("write w.txt", working_dir=str(tmp_path), complete=script, review=False)
    assert (tmp_path / "w.txt").read_text().strip() == "wrapped" and got.met


def test_a_reply_with_a_state_markup_a_fenced_command_or_an_edit_block_is_never_a_report():
    for reply in (MIXED, "STATE: done: x. next: y\n" + "long prose. " * 40, "```bash\nls\n```\n" + "text " * 80, "<invoke name=\"Zzz\">x</invoke> " + "text " * 80):
        assert reads_as_work(reply, parse_reply(reply))
    assert not reads_as_work("The city is Lisbon.", parse_reply("The city is Lisbon."))


def test_a_first_reply_that_mixes_markup_and_state_is_not_met(tmp_path):
    got = run_loop("do it", working_dir=str(tmp_path), complete=Script('<invoke name="Zzz">x</invoke>\nSTATE: done: nothing. next: all of it\nEND STATE\n'), review=False)
    assert not got.met


def test_next_steps_reads_only_what_remains():
    assert next_steps("done: a. learned: b. next: write the file. failed: none") == "write the file."
    assert next_steps("done: all. next: none") == "" and next_steps("done: all. next: report") == "" and next_steps("done: all") == ""
    assert next_steps("done: a. next: nothing left. failed: x") == ""
    assert next_steps("done: all. next: deliver the report.") == "" and next_steps("done: all. next: run CHECK, then report.") == ""      # checking and reporting are the end of the work
    assert next_steps("done: a. next: write b.txt, then report") != ""


def test_a_report_whose_state_still_lists_next_steps_is_refused_and_the_run_goes_on(tmp_path):
    script = Script("RUN: echo a > a.txt\nSTATE: done: a. next: write b.txt\nREPORT: all done\n",
                    "RUN: echo b > b.txt\nSTATE: done: a and b. next: none\nREPORT: wrote both\n")
    got = run_loop("write a.txt and b.txt", working_dir=str(tmp_path), complete=script, review=False)
    assert got.met and got.calls == 2 and (tmp_path / "b.txt").exists()
    assert "not finished" in script.prompts[1] and "BLOCKED" in script.prompts[1]      # the model is told why and how to say a person is needed


def test_a_second_report_with_next_steps_ends_not_met_and_never_as_finished(tmp_path):
    reply = "RUN: echo a > a.txt\nSTATE: done: a. next: write b.txt\nREPORT: all done\n"
    got = run_loop("write a.txt and b.txt", working_dir=str(tmp_path), complete=Script(reply, reply), review=False)
    assert not got.met and got.ended == "unfinished" and "next steps" in got.error and got.report == "all done"


def test_a_run_that_ends_not_met_returns_its_state_never_raw_markup(tmp_path):
    markup = '<invoke name="Zzz"><parameter name="q">x</parameter></invoke>'
    got = run_loop("do it", working_dir=str(tmp_path), complete=Script("RUN: echo a\nSTATE: done: a. next: b\nEND STATE\n", markup, markup), review=False)
    assert not got.met and not says_actions(got.report) and got.report.startswith("done: a")
