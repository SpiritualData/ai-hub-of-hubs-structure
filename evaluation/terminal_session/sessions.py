"""Scripted attended sessions for Terminal Session: a person works with a run while it works, on two different harnesses, and each scenario names the
checks it makes. A scenario returns the names of the checks that failed (empty is right). Free: a scripted completion behind the hub loop, and a fake that
keeps the stream runner's contract; no model, no network. The requirement ids are those of docs/explanation/working-with-the-ai-while-it-works.md."""
import io
import sys
import threading
import time
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import KITS, check, delegate, edit, read, report, run, tree_kit, turn, use  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.session_adapters import report_events  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.session_events import Step, Steer  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import replay, step_row  # noqa: E402


def attend(arm, kit, keys, live=False):
    out = io.StringIO()
    return arm.attend(kit.harness, "do the work", out, keys, tick=0.01, live=live, width=100), out.getvalue()


def done_steps(rep, kind):
    return [e.label for e in rep.events if isinstance(e, Step) and e.kind == kind and e.state == "done"]


def folder_kit(name, turns, **kw):
    folder = tempfile.mkdtemp(prefix="session-")
    Path(folder, "a.txt").write_text("alpha\n")
    return KITS[name](folder, turns, **kw)


def watch(arm, name):
    kit = folder_kit(name, [turn(read("a.txt")), turn(edit("b.txt")), turn(run("echo hi")), turn(report("All done."))], pause=0.01)
    rep, text = attend(arm, kit, ScriptedKeys())
    failed = []
    if [done_steps(rep, k) for k in ("read", "edit", "run")] != [["a.txt"], ["b.txt"], ["echo hi"]]:
        failed.append("steps-with-kind-and-target")
    order = [e.kind for e in rep.events if isinstance(e, Step) and e.state == "done"]
    if order != ["read", "edit", "run"]:
        failed.append("steps-in-order")
    if not (rep.final and rep.final.outcome == "met" and "Changed (1): b.txt" in text):
        failed.append("result-and-changed-files")
    if "calls" not in text:
        failed.append("progress-count")
    if not ("cost unknown" in text or "$" in text) or "$0.0000" in text:
        failed.append("cost-known-or-marked-unknown")
    if "0:0" not in text:
        failed.append("time-shown")
    return failed


def stop_resume(arm, name):
    keys = ScriptedKeys()
    kit = folder_kit(name, [turn(edit("one.txt")), turn(edit("two.txt"), hook=lambda: (keys.press("esc"), keys.press("line", "resume"))),
                            turn(edit("three.txt"), report("All three."))], pause=0.01)
    rep, text = attend(arm, kit, keys)
    failed = []
    first = rep.runs[0] if rep.runs else None
    if not (first and first.outcome == "stopped" and first.session_id):
        failed.append("stop-keeps-session")
    if not Path(kit.folder, "one.txt").exists():
        failed.append("finished-work-kept")
    if len(rep.runs) != 2 or rep.final is None or rep.final.outcome != "met":
        failed.append("resume-finishes")
    names = done_steps(rep, "edit")
    if sorted(names) != ["one.txt", "three.txt", "two.txt"] or len(names) != len(set(names)):
        failed.append("no-step-repeated-after-resume")
    if "resum" not in text:
        failed.append("resume-is-shown")
    return failed


def steer(arm, name):
    keys = ScriptedKeys()
    kit = folder_kit(name, [turn(read("a.txt"), hook=lambda: keys.press("line", "use the short name")), turn(edit("b.txt"), report("Done."))], pause=0.01)
    rep, text = attend(arm, kit, keys)
    failed = []
    if not any(isinstance(c, Steer) and ok for c, ok in rep.controls):
        failed.append("steer-accepted")
    if "you: use the short name" not in text:
        failed.append("shown-as-sent")
    if not any(isinstance(e, Step) and e.kind == "message-received" for e in rep.events) or "taken up" not in text:
        failed.append("shown-as-taken-up")
    if not (kit.trace.heard(1, "use the short name") and not kit.trace.heard(0, "use the short name")):
        failed.append("visible-in-next-call")
    if text.count("use the short name") > 3:
        failed.append("not-restated")
    return failed


def tree(arm, name):
    kit = folder_kit(name, [turn(delegate("write the tests", turn(edit("tests.txt"), report("tests done")))), turn(report("Finished."))], pause=0.01)
    rep, text = attend(arm, kit, ScriptedKeys())
    started = [e for e in rep.events if e.type == "agent-started"]
    failed = []
    if not (len(started) == 1 and started[0].parent_id == "main" and "write the tests" in started[0].task):
        failed.append("helper-under-its-parent")
    if "`- write the tests" not in text:
        failed.append("tree-on-screen")
    if not any(e.type == "agent-ended" and e.state == "met" for e in rep.events):
        failed.append("helper-end-shown")
    return failed


def solution_tree(arm, name):
    node = lambda sid, status, *kids: SimpleNamespace(solution=sid, name=sid.title(), status=status, calls=1, children=list(kids))
    events = report_events(node("a", "met", node("b", "met", node("c", "unmet")), node("d", "met")))
    parents = {e.agent_id: e.parent_id for e in events if e.type == "agent-started"}
    failed = []
    if parents != {"a": "main", "b": "a", "c": "b", "d": "a"}:
        failed.append("three-levels-parentage")
    view = replay(events)
    if view.tree_lines()[:4] != ["main  [running]", "`- A  [met, 1 call]", "   `- B  [met, 1 call]", "      `- C  [unmet, 1 call]"]:
        failed.append("hierarchy-drawn")
    return failed


def approval(arm, name, answer):
    keys = ScriptedKeys()
    seen = {}

    def react(event):
        if event.type == "waiting":
            seen["existed"] = Path(kit.folder, "deployed.txt").exists()
            seen["preview"] = event.preview
            keys.press("line", answer)
    keys.react = react
    kit = folder_kit(name, [turn(use("deploy", "release 1.0")), turn(report("Finished."))], pause=0.01)
    rep, text = attend(arm, kit, keys)
    failed = []
    if "existed" not in seen:
        return ["asks-before-running"]
    if seen["existed"]:
        failed.append("waits-for-the-answer")
    if not seen["preview"] or "It will change" not in text:
        failed.append("preview-before-answer")
    ran = Path(kit.folder, "deployed.txt").exists()
    if (answer == "y") != ran:
        failed.append("runs-only-when-approved")
    if answer == "n":
        if "Blocked or refused" not in text:
            failed.append("refusal-listed-with-reason")
        if not (kit.trace.refused or kit.trace.heard(len(kit.trace.prompts) - 1, "efused")):
            failed.append("harness-told-of-refusal")
    if not (rep.final and rep.final.outcome == "met"):
        failed.append("run-goes-on-after-answer")
    return failed


def target(arm, name):
    keys = ScriptedKeys().when("agent-started", "line", "/stop tests")
    kit = folder_kit(name, [turn(delegate("write the tests", turn(*[edit(f"t{i}.txt") for i in range(8)], report("tests done")))), turn(report("Finished."))], pause=0.05)
    rep, text = attend(arm, kit, keys)
    failed = []
    caps = kit.harness.capabilities
    if not (rep.final and rep.final.outcome == "met"):
        failed.append("rest-of-the-run-goes-on")
    if caps.target_agents:
        ended = [e for e in rep.events if e.type == "agent-ended"]
        if not ended or ended[0].state not in ("failed", "stopped") or len(done_steps(rep, "edit")) >= 8:
            failed.append("helper-stopped-alone")
    elif "cannot stop one agent" not in text:
        failed.append("unavailable-said-plainly")
    return failed


def same_surface(arm, name):
    rows = []
    for kit_name in ("loop", "stream"):
        kit = folder_kit(kit_name, [turn(read("a.txt")), turn(edit("b.txt")), turn(report("All done."))], pause=0.0)
        rep, text = attend(arm, kit, ScriptedKeys())
        rows.append(([(e.kind, e.label) for e in rep.events if isinstance(e, Step) and e.state == "done"], rep.final.outcome if rep.final else "", rep.final.changed if rep.final else ()))
    return [] if rows[0] == rows[1] else ["same-rows-on-two-harnesses"]


def plain_and_replay(arm, name):
    failed = []
    kit = folder_kit(name, [turn(read("a.txt")), turn(edit("b.txt")), turn(report("Done."))], pause=0.0)
    rep, text = attend(arm, kit, ScriptedKeys())
    if "\x1b" in text:
        failed.append("no-escape-codes-off-a-terminal")
    again = replay(rep.events)
    if [step_row(s) for s in again.steps.values()] != [step_row(s) for s in rep.view.steps.values()]:
        failed.append("replay-redraws-the-same-rows")
    kit = folder_kit(name, [turn(read("a.txt")), turn(edit("b.txt")), turn(report("Done."))], pause=0.0)
    rep, text = attend(arm, kit, ScriptedKeys(), live=True)
    if "\x1b[" not in text or "Done: the goal was met" not in text:
        failed.append("redraws-in-place-on-a-terminal")
    return failed


def frame(arm, name):
    holder = {}
    spec = {"solution": "release-notes", "milestone": "ship the next release", "frame": "Notes, then deploy.", "metric": "checks passing",
            "measure": lambda: 3.0 if Path(holder["folder"], "b.txt").exists() else 1.0}
    folder = tempfile.mkdtemp(prefix="session-")
    holder["folder"] = folder
    kit = KITS[name](folder, [turn(edit("b.txt")), turn(report("Done."))], pause=0.0, frame=spec)
    rep, text = attend(arm, kit, ScriptedKeys())
    failed = []
    if "Served: release-notes | milestone: ship the next release" not in text:
        failed.append("solution-and-milestone-shown")
    if "Frame: Notes, then deploy." not in text:
        failed.append("frame-shown")
    if "before 1, after 3 (+2)" not in text:
        failed.append("metric-before-and-after")
    return failed


def live_helper(arm, name):
    """The loop itself reports a helper as it starts and ends, and the helper's own steps under it (no guessing from its end)."""
    kit = folder_kit(name, [turn(delegate("write the tests", turn(read("a.txt"), edit("tests.txt"), report("tests done")))), turn(report("Finished."))], pause=0.01)
    rep, text = attend(arm, kit, ScriptedKeys())
    kinds = [(e.type, getattr(e, "agent_id", "")) for e in rep.events]
    failed = []
    started = [i for i, e in enumerate(rep.events) if e.type == "agent-started"]
    own = [i for i, e in enumerate(rep.events) if isinstance(e, Step) and e.agent_id != "main" and e.kind == "edit"]
    ended = [i for i, e in enumerate(rep.events) if e.type == "agent-ended"]
    if not (len(started) == 1 and own and ended and started[0] < own[0] < ended[0]):
        failed.append("helper-announced-before-its-steps")
    if own and rep.events[own[0]].agent_id != rep.events[started[0]].agent_id:
        failed.append("helper-steps-under-the-helper")
    if "     tests.txt" not in text and "tests.txt" not in text:
        failed.append("helper-edit-shown")
    return failed


def stop_prompt(arm, name):
    """A stop during a slow model call returns at once (not after the call) and the session resumes from before that call."""
    keys = ScriptedKeys()
    hold = lambda: (keys.press("esc"), keys.press("line", "resume"), time.sleep(6))
    kit = folder_kit(name, [turn(edit("one.txt")), turn(edit("two.txt"), hook=hold), turn(edit("two.txt")), turn(edit("three.txt"), report("All three."))], pause=0.0)
    begun = time.monotonic()
    out = io.StringIO()
    holder = {}

    def watch_first_stop():
        pass
    rep = arm.attend(kit.harness, "do the work", out, keys, tick=0.01, live=False, width=100)
    first = rep.runs[0] if rep.runs else None
    failed = []
    stopped_at = next((e.at for e in rep.events if e.type == "finished"), 99)
    if not (first and first.outcome == "stopped" and stopped_at < 2.5):
        failed.append("stop-returns-within-two-seconds")
    names = done_steps(rep, "edit")
    if sorted(names) != ["one.txt", "three.txt", "two.txt"] or len(names) != 3:
        failed.append("resume-after-an-abandoned-call")
    return failed


def solution_agents(arm, name):
    """A tree of solution workers is a tree of agents with their solutions, and each worker's steps sit under its own solution."""
    folder = tempfile.mkdtemp(prefix="session-")
    kit = tree_kit(folder, {"release": ["notes", "tests"], "tests": ["fixtures"]})
    rep, text = attend(arm, kit, ScriptedKeys())
    parents = {e.solution: e.parent_id for e in rep.events if e.type == "agent-started"}
    ids = {e.solution: e.agent_id for e in rep.events if e.type == "agent-started"}
    failed = []
    if set(parents) != {"release", "notes", "tests", "fixtures"} or parents["release"] != "main" or parents["notes"] != ids["release"] or parents["fixtures"] != ids["tests"]:
        failed.append("agents-follow-the-solution-hierarchy")
    under = {e.agent_id for e in rep.events if isinstance(e, Step) and e.kind == "edit"}
    if under != set(ids.values()):
        failed.append("each-worker-steps-under-its-solution")
    if "(fixtures)" not in text or "Served: release" not in text:
        failed.append("solutions-shown")
    return failed


def check_never_passes(arm, name):
    """A task whose check can never pass ends with an honest partial report after at most two failed checks, and the person sees that report."""
    turns = [turn(run("echo did the part"), check("echo missing facts >&2; exit 1"), report("A person must supply the facts for rows 3 to 5."))] * 3
    kit = folder_kit(name, turns, pause=0.0)
    rep, text = attend(arm, kit, ScriptedKeys())
    failed_checks = [e for e in rep.events if isinstance(e, Step) and e.kind == "check" and e.state == "failed"]
    failed = []
    if len(failed_checks) > 2 or kit.trace.calls > 2:
        failed.append("ends-after-two-failed-checks")
    if not (rep.final and rep.final.outcome == "unmet" and "A person must supply the facts" in rep.final.report):
        failed.append("partial-report-is-the-output")
    if "A person must supply the facts" not in text:
        failed.append("partial-report-shown")
    return failed


def repeat_refused(arm, name):
    """A failing command repeated is refused on the third try (it is not run again) and the person sees why."""
    command = "echo x >> n.txt; echo boom >&2; exit 1"
    kit = folder_kit(name, [turn(run(command))] * 4 + [turn(report("Could not do it: the command fails with boom."))], pause=0.0)
    rep, text = attend(arm, kit, ScriptedKeys())
    runs = Path(kit.folder, "n.txt").read_text().count("x")
    failed = []
    if runs != 2:
        failed.append("not-run-the-third-time")
    refused = [e for e in rep.events if isinstance(e, Step) and e.kind == "run" and e.state == "failed" and "not run" in e.detail]
    if not refused:
        failed.append("refusal-shown-with-its-reason")
    if not (rep.final and "Could not do it" in rep.final.report):
        failed.append("run-ends-with-its-report")
    return failed


SCENARIOS = {"check_never_passes": check_never_passes, "repeat_refused": repeat_refused, "live_helper": live_helper, "stop_prompt": stop_prompt, "solution_agents": solution_agents, "watch": watch, "stop_resume": stop_resume, "steer": steer, "tree": tree, "solution_tree": solution_tree,
             "approve": lambda arm, name: approval(arm, name, "y"), "refuse": lambda arm, name: approval(arm, name, "n"), "target": target,
             "same_surface": same_surface, "plain_and_replay": plain_and_replay, "frame": frame}


SECONDS = 8


def run_scenario(arm, scenario, kit):
    """The failed checks of a scenario. An arm that cannot take a key while a run works (a question nobody can answer) hangs, which is a failure."""
    done = {}

    def work():
        try:
            done["failed"] = SCENARIOS[scenario](arm, kit)
        except Exception as error:  # noqa: BLE001 -- an arm that cannot do the scenario fails it
            done["failed"] = [f"raised {type(error).__name__}"]
    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(SECONDS)
    return done.get("failed", ["hung waiting for the person"])
