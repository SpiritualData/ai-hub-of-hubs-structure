"""Scenarios taken from what the reviewed terminals document and from the consumer's own requirement tests, not from any arm of this solution: a refused command shows its
reason (Claude Code lists a denied tool, Codex and Crush ask before a command), a helper's file counts as changed (Codex lists file-change items), a run is not met while a
helper still works, the first seconds show a start, a message typed during a run is shown as queued until it is read (Claude Code queues it), a question from a helper names the
helper (Claude Code), the answer's markdown is rendered (Aider renders it), a stopped run keeps what it had written and names the command that resumes it (Aider keeps the
partial answer; Codex and Claude Code resume by id), and a run that changed nothing says so (the consumer's result probe). Each one drives the arm through ``attend`` with
the raw lines of a stream-json session or with typed events, never with a script that knows the arm. Returns the names of the checks that failed; free, no model."""
import io
import threading
import time

from sessions import attend  # noqa: F401  (shared helper of the sibling scenarios)

from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Capabilities, Finished, RunStarted, Step, Steer, Stop, Waiting)
from hubofhubs.the_consciousness.ai_session_experience.session_harnesses import StreamHarness
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent

INIT = {"type": "system", "subtype": "init", "session_id": "sess-doc"}
RESULT = {"type": "result", "total_cost_usd": 0.012, "num_turns": 4, "usage": {"input_tokens": 100, "output_tokens": 40}}


def use(ident, name, given, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent, "message": {"content": [{"type": "tool_use", "id": ident, "name": name, "input": given}]}}


def done(ident, text="ok", error=False, parent=None):
    return {"type": "user", "parent_tool_use_id": parent, "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "content": text, "is_error": error}]}}


class Raw:
    """A runner with the stream contract that forwards raw stream-json lines as progress events, as the real one does."""

    def __init__(self, lines, output="Done.", met=True, hold=0.0, hook=None, unseen=()):
        self.lines, self.output, self.met, self.hold, self.hook, self.unseen = lines, output, met, hold, hook, unseen

    def run_goal(self, *, goal, brief, emit, run_id, resume_session_id, cancel_check, control):
        for raw in self.lines:
            emit(ProgressEvent(type="stream", text="", data=raw))
            time.sleep(0.01)
        if self.hook:
            self.hook()
        waited = 0.0
        while waited < self.hold and not cancel_check():
            time.sleep(0.02)
            waited += 0.02
        cancelled = bool(cancel_check())
        return DeepResult(met=self.met and not cancelled, output=self.output, session_id="sess-doc", cancelled=cancelled, unseen_inputs=list(self.unseen), cost_usd=0.012)


def attend_raw(arm, runner, keys=None, live=False):
    out = io.StringIO()
    rep = arm.attend(StreamHarness(runner, root="/work"), "do the work", out, keys or ScriptedKeys(), tick=0.01, live=live, width=100)
    return rep, out.getvalue()


def refused_reason(arm, name):
    lines = [INIT, use("t1", "Bash", {"command": "rm -rf build"}),
             done("t1", "Claude requested permissions to use Bash, but you haven't granted it yet.", error=True), RESULT]
    rep, text = attend_raw(arm, Raw(lines, output="I could not run the command."))
    failed = []
    if not any(isinstance(e, Step) and e.state == "blocked" and "permission" in e.detail for e in rep.events):
        failed.append("refused-step-carries-its-reason")
    if text.count("haven't granted") < 1 and text.count("permission") < 2:
        failed.append("reason-on-screen")
    if "Blocked or refused" not in text:
        failed.append("listed-at-the-end")
    return failed


def helper_file_counts(arm, name):
    lines = [INIT, use("a1", "Task", {"description": "write the tests"}), use("w1", "Write", {"file_path": "/work/tests/t1.txt"}, parent="a1"), done("w1", parent="a1"),
             done("a1", "tests written"), RESULT]
    rep, text = attend_raw(arm, Raw(lines))
    failed = []
    if "Changed (1): tests/t1.txt" not in text:
        failed.append("helper-file-in-changed-relative-to-the-folder")
    started = [e for e in rep.events if isinstance(e, AgentStarted)]
    if not (started and any(isinstance(e, Step) and e.agent_id == started[0].agent_id and e.kind == "edit" for e in rep.events)):
        failed.append("helper-step-under-its-helper")
    return failed


def not_met_while_helper_runs(arm, name):
    lines = [INIT, use("a1", "Task", {"description": "long background check"}), RESULT]
    rep, text = attend_raw(arm, Raw(lines, output="Started a check in the background."))
    failed = []
    if rep.final is None or rep.final.outcome == "met":
        failed.append("not-met-while-a-helper-runs")
    elif "helper" not in (rep.final.error + text).lower():
        failed.append("says-which-helper-is-still-running")
    return failed


def first_seconds(arm, name):
    """The run says it started before the first model line arrives."""
    runner = Raw([INIT], hold=0.0)
    first = {}

    class Slow(Raw):
        def run_goal(self, **kw):
            time.sleep(0.4)
            return super().run_goal(**kw)
    rep, text = attend_raw(arm, Slow([INIT, use("r1", "Read", {"file_path": "/work/a.txt"}), done("r1"), RESULT]))
    kinds = [(e.type, getattr(e, "label", "")) for e in rep.events[:3]]
    failed = []
    if not (rep.events and rep.events[0].type == "run-started" and rep.events[0].at < 0.35):
        failed.append("start-event-before-the-first-line")
    if "❯" not in text:         # the goal is the person's own message, shown at once (revision of 2026-11-11: it was a "started" line)
        failed.append("start-shown-on-screen")
    return failed


def queued_until_read(arm, name):
    keys = ScriptedKeys()
    runner = Raw([INIT, use("r1", "Read", {"file_path": "/work/a.txt"}), done("r1")], hold=0.5, hook=lambda: keys.press("line", "use the short name"), unseen=("use the short name",), met=False)
    rep, text = attend_raw(arm, runner, keys)
    failed = []
    if "you: use the short name" not in text:
        failed.append("sent-message-shown")
    if "queued" not in text and "taken up" not in text:
        failed.append("queued-or-taken-up-said")
    if "Not yet taken up" not in text:
        failed.append("unread-message-listed-at-the-end")
    return failed


class Asking:
    name = "asking"
    capabilities = Capabilities(stop=True, resume=True, steer=False, approve=True)

    def __init__(self, keys):
        self.keys = keys

    def start(self, goal, sink, resume_session_id=""):
        sink(RunStarted(goal=goal, harness="asking"))
        sink(AgentStarted(agent_id="h1", task="write the migration"))
        sink(Waiting(agent_id="h1", ask_id="q1", question="Run the migration?", preview="changes 3 tables"))
        time.sleep(0.15)
        sink(AgentEnded(agent_id="h1", state="met"))
        end = Finished(outcome="met", report="Done.", session_id="s1")
        sink(end)
        return end

    def control(self, control):
        return True


def helper_question_named(arm, name):
    keys = ScriptedKeys().when("waiting", "line", "y")
    out = io.StringIO()
    arm.attend(Asking(keys), "do the work", out, keys, tick=0.01, live=False, width=100)
    return [] if "write the migration" in out.getvalue().split("Waiting for you")[-1].split("\n")[0] else ["helper-named-in-its-question"]


def markdown_answer(arm, name):
    answer = "# Result\n\nThe **fast** path uses `cache`.\n\n- first point\n- second point\n\n```\nrun --now\n```"
    rep, text = attend_raw(arm, Raw([INIT, RESULT], output=answer), live=True)
    failed = []
    shown = text.split("Result", 1)[-1]
    if "**fast**" in shown or "# Result" in text or "```" in text:
        failed.append("markdown-marks-not-shown-raw")
    if "first point" not in text or "run --now" not in text:
        failed.append("content-kept")
    return failed


def stopped_keeps_and_names_resume(arm, name):
    keys = ScriptedKeys()
    runner = Raw([INIT, use("w1", "Write", {"file_path": "/work/one.txt"}), done("w1")], hold=5.0, hook=lambda: keys.press("esc"), output="Partial: wrote one.txt.")
    rep, text = attend_raw(arm, runner, keys)
    failed = []
    if not (rep.runs and rep.runs[0].outcome == "stopped"):
        failed.append("stop-ends-the-run-as-stopped")
    if "one.txt" not in text:
        failed.append("finished-work-still-shown")
    if "--resume sess-doc" not in text:
        failed.append("resume-command-named")
    return failed


def nothing_changed(arm, name):
    rep, text = attend_raw(arm, Raw([INIT, use("r1", "Read", {"file_path": "/work/a.txt"}), done("r1"), RESULT], output="Nothing to change."))
    return [] if "no files changed" in text else ["says-nothing-changed"]       # in the outcome line (revision of 2026-11-11: it was a "Changed (0): nothing" line)


SCENARIOS = {"refused_reason": refused_reason, "helper_file_counts": helper_file_counts, "not_met_while_helper_runs": not_met_while_helper_runs,
             "first_seconds": first_seconds, "queued_until_read": queued_until_read, "helper_question_named": helper_question_named,
             "markdown_answer": markdown_answer, "stopped_keeps_and_names_resume": stopped_keeps_and_names_resume, "nothing_changed": nothing_changed}
