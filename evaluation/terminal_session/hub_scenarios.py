"""Scripted scenarios for what is unique to the hub in the terminal: the structure of the work (collapsed, toggled and opened on request), the ceilings against spend and
time, the soft-limit line, the hub's stop decision, the end of a run, a follow-up that continues the session, a switch of harness between runs, the prompt with no goal and
the Representative the AI acts for. Each returns the names of the checks that failed (empty is right); free, no model. Requirement ids X24 to X33 are in
docs/explanation/working-with-the-ai-while-it-works.md."""
import io
import tempfile
from pathlib import Path

from sessions import folder_kit  # noqa: F401  (the shared folder helper of the sibling scenarios)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import (
    decide, delegate, edit, loop_kit, outside, read, refuse_round, report, soft_limit, stream_kit, turn)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import frame

SOLUTION = {"solution_id": "the-mind", "name": "The Mind", "purpose": "Think well.", "approach": "Weigh the evidence.", "out_of_scope": "", "authoritative_metric_id": "m1",
            "selected": "arm", "milestones": "", "problem_ids": "", "ideal_ids": "", "delegates_to": "memory"}
TABLES = {"solutions": [SOLUTION, {**SOLUTION, "solution_id": "memory", "name": "Memory", "purpose": "Remember what matters.", "authoritative_metric_id": "", "delegates_to": ""}],
          "problems": [], "ideals": [], "implementations": [], "metrics": [{"metric_id": "m1", "name": "Recall", "command": ""}],
          "results": [{"component": "the_mind", "impl": "arm", "balanced": "0.9", "passed": "9/10", "cases": "10", "date": "2026-11-01"}]}
FRAME = {"solution": "the-mind", "milestone": "think better"}


def folder() -> str:
    path = tempfile.mkdtemp(prefix="session-")
    Path(path, "a.txt").write_text("alpha\n")
    return path


def attend(arm, kit, keys, **options):
    out = io.StringIO()
    rep = arm.attend(kit.harness, "do the work", out, keys, tick=0.01, live=False, width=100, **options)
    return rep, out.getvalue()


def work(arm, kits, lines, **options):
    out = io.StringIO()
    names = list(kits)
    terminal = arm.work(lambda name: kits[name].harness, out, lines=lines, harness=names[0], names=names, tick=0.01, live=False, width=100, **options)
    return terminal, out.getvalue()


def plain(text):
    return [] if "\x1b[" not in text else ["no-escape-codes-off-a-terminal"]


def helper_turns(keys, *presses, after=1):
    """A helper on a named solution, then a turn whose start presses the keys (so the helper's events are already in)."""
    return [turn(delegate("[memory] check it", turn(edit("m.txt"), report("ok")))), turn(read("a.txt"), hook=lambda: [keys.press(p) for p in presses]), turn(report("Done."))]


def structure_toggle(arm, name):
    keys = ScriptedKeys()
    kit = stream_kit(folder(), helper_turns(keys, "tree", "tree"), frame=FRAME)
    rep, text = attend(arm, kit, keys, records=TABLES)
    rows = [line for line in text.splitlines() if line.strip().lstrip("> ").startswith(("+", "-")) and ("(the-mind)" in line or "(memory)" in line)]
    failed = plain(text)
    if "purpose:" in text.split("structure (")[0]:
        failed.append("collapsed-by-default")
    if text.count("structure (") != 1:
        failed.append("tab-shows-then-hides")
    if not (len(rows) >= 2 and rows[0].index("The Mind") < rows[1].index("Memory")):
        failed.append("helper-solution-under-the-run-solution")
    if rep.view.show_structure:
        failed.append("toggle-off-leaves-it-hidden")
    return failed


def structure_expand(arm, name):
    keys = ScriptedKeys()
    kit = stream_kit(folder(), helper_turns(keys, "tree", "open", "down", "open"), frame=FRAME)
    rep, text = attend(arm, kit, keys, records=TABLES)
    failed = plain(text)
    if "purpose: Think well." not in text or "metric: Recall: 0.9" not in text:
        failed.append("selected-solution-fields")
    if "delegates to Memory: Remember what matters." not in text:
        failed.append("connections-shown")
    if text.index("purpose: Think well.") > text.index("purpose: Remember what matters."):
        failed.append("only-the-selected-solution-opens-first")
    if sorted(rep.view.opened) != ["memory", "the-mind"]:
        failed.append("opened-solutions-kept")
    return failed


def ceiling_status(arm, name):
    # revision of 2026-11-11: a ceiling is named in the header only once half of it is used (the records ask for quiet appearance), so the spend ceiling is set low enough for the
    # scripted run to use more than half of it and the time ceiling high enough that it does not
    kit = stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))], limits=(0.01, 1800.0))
    rep, text = attend(arm, kit, ScriptedKeys())
    head = frame(rep.view, 100)[0]
    failed = plain(text)
    if "of $0.01" not in head:
        failed.append("spent-against-the-ceiling-once-half-used")
    if "of 30:00" in head:
        failed.append("time-ceiling-quiet-while-little-is-used")
    if "of $0.01" not in text:
        failed.append("plain-line-has-the-ceiling")
    bare = stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))])
    rep2, _ = attend(arm, bare, ScriptedKeys())
    if " of " in frame(rep2.view, 100)[0].replace("Hub of Hubs", ""):      # the product's name has an "of" in it
        failed.append("no-ceiling-no-segment")
    return failed


def soft_limit_line(arm, name):
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(soft_limit(), edit("two.txt")), turn(report("Wrapped up."))], limits=(0.01, 1800.0))
    rep, text = attend(arm, kit, ScriptedKeys())
    failed = plain(text)
    lines = [line for line in text.splitlines() if "wrapping up:" in line]
    if len(lines) != 1 or "safe stopping point" not in lines[0] or "spend ceiling" not in lines[0]:
        failed.append("one-line-saying-it-is-wrapping-up-and-why")
    if not rep.view.soft_limit:
        failed.append("state-kept")
    return failed


def stop_decision_line(arm, name):
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(decide("code_finding"), edit("two.txt")), turn(refuse_round("resume_limit"), report("Done."))])
    rep, text = attend(arm, kit, ScriptedKeys())
    failed = plain(text)
    if "hub decision: go on, the check found something to fix" not in text:
        failed.append("continue-decision-with-reason")
    if "hub decision: stop, it already went round once more" not in text:
        failed.append("stop-decision-with-reason")
    if "Left: " not in text or "chose not to go round again" not in text:
        failed.append("left-says-why-it-stopped")
    return failed


def end_of_run(arm, name):
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(outside("wrote notes.txt outside the folder"), report("Wrote one.txt."))])
    rep, text = attend(arm, kit, ScriptedKeys())
    failed = plain(text)
    if "Wrote one.txt." not in text or "Changed (1): one.txt" not in text:
        failed.append("what-was-done")
    if not any(line.startswith("ahohs work --resume sess-") and "--harness stream" in line for line in text.splitlines()):       # the command whole on its own line (revision of 2026-11-11)
        failed.append("how-to-resume-the-command")
    if "Outside the folder (report only" not in text or "wrote notes.txt outside the folder" not in text:
        failed.append("outside-folder-report")
    return failed


def follow_up_continues(arm, name):
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(report("First done."))])
    kit.runner.followups = [[turn(edit("two.txt"), report("Second done."))]]
    terminal, text = work(arm, {"stream": kit}, ["start", "and also two", "/quit"])
    first, second = (terminal.reports + [None, None])[:2]
    failed = plain(text)
    if second is None or not (second.events and second.events[0].type == "run-started" and second.events[0].resumed):
        return failed + ["follow-up-resumes-the-session"]
    if first.final.session_id != second.final.session_id:
        failed.append("same-session")
    if not Path(kit.folder, "two.txt").exists() or second.final.report != "Second done.":
        failed.append("follow-up-does-the-new-work")
    if "> " not in text:
        failed.append("prompt-offered-after-the-run")
    return failed


def harness_switch(arm, name):
    stream = stream_kit(folder(), [turn(edit("one.txt")), turn(report("First done."))])
    loop = loop_kit(folder(), [turn(edit("l.txt"), report("Loop done."))])
    terminal, text = work(arm, {"stream": stream, "loop": loop}, ["first goal", "/harness nope", "/harness loop", "second goal", "/quit"])
    failed = plain(text)
    if len(terminal.reports) != 2:
        return failed + ["both-runs-happen"]
    one, two = terminal.reports
    if two.events[0].harness != "loop" or two.events[0].resumed or two.final.session_id == one.final.session_id:
        failed.append("new-session-on-the-new-harness")
    if not loop.trace.heard(0, "Earlier in this conversation"):
        failed.append("recap-of-the-earlier-run-given")
    if "no harness named 'nope'" not in text:
        failed.append("unknown-name-refused")
    if [r.final.outcome for r in terminal.reports] != ["met", "met"]:
        failed.append("both-end-met")
    return failed


def no_goal_prompt(arm, name):
    kit = stream_kit(folder(), [turn(edit("one.txt")), turn(report("Done."))])
    terminal, text = work(arm, {"stream": kit}, ["", "do it", "/quit"])
    failed = plain(text)
    if text.count("Type a goal") != 1 or not text.startswith("Type a goal"):
        failed.append("one-line-hint-then-prompt")
    if len(terminal.reports) != 1 or terminal.reports[0].view.goal != "do it":
        failed.append("blank-line-runs-nothing-and-the-goal-runs")
    return failed


def representative(arm, name):
    from hubofhubs.the_consciousness.representatives.representatives import DeclaredAuthority
    reps = DeclaredAuthority({"alex": {"authority": {"allow": ["web-search", "files"], "ask": {"outward": "always"}}, "preferences": {"iteration": {"one_pass": True}}}, "sam": {}})
    keys = ScriptedKeys()
    kit = stream_kit(folder(), [turn(read("a.txt"), hook=lambda: keys.press("tree")), turn(report("Done."))])
    terminal, text = work(arm, {"stream": kit}, ["/as", "/as nobody", "/as sam", "first", "/who", "/quit"], keys=keys, represent=reps.represent, people=("alex", "sam"), person="alex")
    failed = plain(text)
    for wanted in ("* alex", "no representative named 'nobody'", "now acting for sam"):
        if wanted not in text:
            failed.append("as-lists-and-switches:" + wanted)
    if not terminal.reports or terminal.reports[0].view.acting_for != "sam":
        failed.append("segment-names-who-the-ai-acts-for")
    if " · for sam" not in frame(terminal.reports[0].view, 100)[0]:
        failed.append("quiet-header-segment")
    kit2 = stream_kit(folder(), [turn(read("a.txt"), hook=lambda: keys.press("tree")), turn(report("Done."))])
    from hubofhubs.the_consciousness.representatives.stop_limits import resolve_stop_limits
    alex = reps.represent("alex")
    rep, shown = attend(arm, kit2, keys, representative=alex, stop_limits=resolve_stop_limits(alex))
    for wanted in ("acting for: alex", "worker categories allowed: web-search, files", "data scope: alex", "asking policy: outward: always", "stop limits: one pass only"):
        if wanted not in shown:
            failed.append("authority-in-the-opened-view:" + wanted)
    bare = stream_kit(folder(), [turn(read("a.txt")), turn(report("Done."))])
    rep3, plain_text = attend(arm, bare, ScriptedKeys())
    if "acting for" in plain_text or "| for " in frame(rep3.view, 100)[0]:
        failed.append("nothing-extra-without-a-representative")
    return failed


SCENARIOS = {"structure_toggle": structure_toggle, "structure_expand": structure_expand, "ceiling_status": ceiling_status, "soft_limit_line": soft_limit_line,
             "stop_decision_line": stop_decision_line, "end_of_run": end_of_run, "follow_up_continues": follow_up_continues, "harness_switch": harness_switch,
             "no_goal_prompt": no_goal_prompt, "representative": representative}
