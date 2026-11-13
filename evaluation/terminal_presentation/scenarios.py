"""Scripted sessions for the presentation metric: the same scripts for every arm, run on a scripted fake harness (no model, no network) at each stated size, each scenario
naming the checks it makes. A scenario returns ``{"checks": {name: True | False | None}, "ceiling": {name: bool}, "not_run": [names]}``; a check that fails at either size
fails. The scripted harnesses are the hub's own (``terminal_experience.scripted``)."""
from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import checks as C  # noqa: E402
from screen import SIZES, Capture, plain_capture, stream_capture, textual_capture  # noqa: E402

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import (  # noqa: E402
    delegate, edit, read, report, run, stream_kit, turn, use)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys  # noqa: E402

PAUSE = 0.2
ALL_CHECKS = tuple(C.REQUIREMENTS)
DRAWN = threading.local()        # the captures the scenario running in this thread has made


def folder() -> str:
    path = tempfile.mkdtemp(prefix="presentation-")
    Path(path, "a.txt").write_text("alpha\n")
    return path


def presentation_of(arm: Any) -> str:
    """How an arm is captured: its own ``presentation`` (``stream``, ``textual`` or ``external``), else ``textual`` when it hosts a Textual application, else ``stream``."""
    return getattr(arm, "presentation", None) or ("textual" if hasattr(arm, "attending") else "stream")


def textual_hooks(arm: Any) -> Dict[str, Any]:
    """The capture hook of a Textual arm that has its own application and transcript class (``polished_session``: added 2026-11-11 when that arm was first scored, so it is drawn by
    its own screen and not by ``textual_session``'s; no check or weight was changed). Any other Textual arm is drawn by the default hooks."""
    if arm.__class__.__module__.endswith("polished.session"):
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.app import PolishedApp, Transcript
        return {"make_app": lambda: PolishedApp(title=arm.title), "transcript_class": Transcript}
    own = getattr(arm, "capture_hooks", None)       # an arm that brings its own application and transcript says how it is drawn (``adopted_session``: added 2026-11-11, no check or weight changed)
    return own() if callable(own) else {}


def capture(arm: Any, kit: Any, keys: Any, size: Tuple[int, int], options: Optional[Dict[str, Any]] = None) -> Capture:
    goal = getattr(kit, "goal", "do the work")
    if presentation_of(arm) == "textual":
        cap = textual_capture(arm, kit.harness, keys, size, goal=goal, options=options, **textual_hooks(arm))
    else:
        cap = stream_capture(arm, kit.harness, keys, size, goal=goal, options=options)
    cap.labels = dict(getattr(arm, "screen_labels", None) or {})        # what the arm declares its screen says for each control and role (nothing declared: the hub's shared words)
    getattr(DRAWN, "caps", []).append(cap)       # every screen a scenario draws is judged by the capitalisation policy (``run_scenario``)
    return cap


def both(arm: Any, build: Callable[[ScriptedKeys], Any], options: Optional[Dict[str, Any]] = None) -> List[Capture]:
    caps = []
    for size in SIZES:
        keys = ScriptedKeys()
        caps.append(capture(arm, build(keys), keys, size, options))
    return caps


def over(caps: Sequence[Capture], check: Callable[[Capture], Optional[bool]]) -> Optional[bool]:
    return C.combine([check(c) for c in caps])


def rendering(caps: Sequence[Capture]) -> Dict[str, Optional[bool]]:
    return {"each-update-once": over(caps, C.each_update_once), "no-row-wider-than-the-terminal": over(caps, C.no_row_wider_than_the_terminal),
            "repaints-under-bound": over(caps, C.repaints_under_bound), "contrast-4.5": over(caps, C.contrast_ok)}


# --- scenarios ----------------------------------------------------------------------------------------------------------------------

def watch(arm: Any) -> Dict[str, Any]:
    caps = both(arm, lambda keys: stream_kit(folder(), [turn(read("a.txt")), turn(edit("b.txt")), turn(delegate("write the tests", turn(edit("tests.txt"), report("tests done")))),
                                                      turn(run("echo hi")), turn(report("All done."))], pause=PAUSE))
    return {"checks": {**rendering(caps), "current-step-visible": over(caps, C.current_step_visible), "closing-report-complete": over(caps, C.closing_report_complete),
                       "first-output-within-a-second": over(caps, C.first_output), "key-hints-present-and-whole": C.key_hints(caps)},
            "ceiling": ceilings(arm)["ceiling"]}       # what only the hub can show is read in the same case, as its own column


def revision_2(caps: Sequence[Capture]) -> Dict[str, Optional[bool]]:
    """The checks added in revision 2 (2026-11-11), each over every size."""
    return {"no-raw-markdown": over(caps, C.no_raw_markdown), "no-internal-vocabulary": over(caps, C.no_internal_vocabulary), "answer-once": over(caps, C.answer_once),
            "no-empty-figure-segment": over(caps, C.no_empty_figure_segment), "resume-command-unbroken": over(caps, C.resume_command_unbroken),
            "header-has-full-name": over(caps, C.header_has_full_name), "no-stray-leading-padding": over(caps, C.no_stray_leading_padding),
            "cost-at-cent-precision": over(caps, C.cost_at_cent_precision), "goal-as-persons-message": over(caps, C.goal_as_message)}


def pasted_run(arm: Any) -> Dict[str, Any]:
    """The run the owner pasted (``pasted.py``), drawn at every size and judged by the revision 2 checks, with the closing report and the header."""
    import pasted
    caps = both(arm, lambda keys: pasted.Kit())
    return {"checks": {**revision_2(caps), "closing-report-complete": over(caps, C.closing_report_complete), "no-row-wider-than-the-terminal": over(caps, C.no_row_wider_than_the_terminal)}}


def real_run(arm: Any) -> Dict[str, Any]:
    """A real native run's recorded events (``real_native_run.json``: the interim note is the answer cut with three dots, three figure updates come before the finish), drawn at every size: the
    answer is on the screen once, the markdown is drawn, the closing is complete."""
    import real_run as recorded
    caps = both(arm, lambda keys: recorded.Kit())
    return {"checks": {"answer-once": over(caps, C.answer_once), "no-raw-markdown": over(caps, C.no_raw_markdown), "closing-report-complete": over(caps, C.closing_report_complete),
                       "no-row-wider-than-the-terminal": over(caps, C.no_row_wider_than_the_terminal)}}


def steer(arm: Any) -> Dict[str, Any]:
    def build(keys: Any) -> Any:
        return stream_kit(folder(), [turn(read("a.txt"), hook=lambda: keys.press("line", "use the short name")), turn(edit("b.txt")), turn(edit("c.txt"), report("Done."))], pause=PAUSE)
    caps = both(arm, build)
    return {"checks": {"correction-sent-then-taken-up": over(caps, C.correction_sent_then_taken_up),
                       "round-trip-steer": over(caps, lambda c: C.round_trip(c, "steer", r"you: use the short name|use the short name", "use the short name"))},
            "ceiling": {"correction-taken-up": bool(over(caps, C.correction_sent_then_taken_up))}}


def stop_resume(arm: Any) -> Dict[str, Any]:
    def build(keys: Any) -> Any:
        # the person presses Escape and, as in real use, the screen waits in its stopped state until they type resume a moment later (a stop that resumed in the same instant
        # left no screen to read an acknowledgement from; revision 2 made the scenario wait, which changes no check)
        keys.waits_for_input = True
        return stream_kit(folder(), [turn(edit("one.txt")), turn(edit("two.txt"), hook=lambda: (keys.press("esc"), threading.Timer(0.5, lambda: keys.press("line", "resume")).start())),
                                     turn(edit("three.txt"), report("All three."))], pause=PAUSE)
    caps = both(arm, build)
    return {"checks": {"stop-then-resume-keeps-work": over(caps, C.stop_then_resume_keeps_work), "round-trip-stop": over(caps, lambda c: C.round_trip(c, "stop", r"stopp|type resume|resume to continue")),       # the state after a stop: the word stopped, or the line that says how to resume (the header now shows the state as a glyph)
                       "round-trip-resume": over(caps, lambda c: C.combine([bool(c.report and len(c.report.runs) >= 2 and "resum" in c.all_text().lower())])),
                       "closing-report-complete": over(caps, C.closing_report_complete)}}


def approval(arm: Any, answer: str) -> Dict[str, Any]:
    def build(keys: Any) -> Any:
        def react(event: Any) -> None:
            if event.type == "waiting":
                threading.Timer(0.8, lambda: keys.press("line", answer)).start()
        keys.react = react
        return stream_kit(folder(), [turn(use("deploy", "release 1.0")), turn(report("Finished."))], pause=0.0)
    caps = both(arm, build)
    word = "approve" if answer == "y" else "refuse"
    shown = r"deploy" if answer == "y" else r"refus|blocked"
    out = {"risky-step-waits-with-preview": over(caps, C.risky_step_waits_with_preview), f"round-trip-{word}": over(caps, lambda c: C.round_trip(c, word, shown))}
    return {"checks": out}


def target(arm: Any) -> Dict[str, Any]:
    def build(keys: Any) -> Any:
        keys.when("agent-started", "line", "/stop tests")
        return stream_kit(folder(), [turn(delegate("write the tests", turn(*[edit(f"t{i}.txt") for i in range(6)], report("tests done")))), turn(report("Finished."))], pause=0.3)     # 0.3 s a step (was 0.1): on a loaded machine the helper could end before the key reached it, a timing flake seen once in 21 runs of live_session
    caps = both(arm, build)
    return {"checks": {"unavailable-control-shown": over(caps, C.unavailable_shown)},
            "ceiling": {"stop-one-helper": all(any(c2.type == "stop" and c2.agent_id for _, c2, _ in cap.controls) for cap in caps)}}


def plain(arm: Any) -> Dict[str, Any]:
    kit = stream_kit(folder(), [turn(read("a.txt")), turn(edit("b.txt"), report("Done."))], pause=0.0)
    text, rep = plain_capture(arm, kit.harness, ScriptedKeys())
    return {"checks": {"plain-when-not-a-terminal": C.plain_text(text, ["a.txt", "b.txt"], rep.final.report if rep and rep.final else "")}}


def ceilings(arm: Any) -> Dict[str, Any]:
    def build(keys: Any) -> Any:
        return stream_kit(folder(), [turn(read("a.txt"), hook=lambda: keys.press("tree")), turn(delegate("write the tests", turn(edit("t.txt"), report("ok")))),
                                     turn(edit("b.txt")), turn(report("Done."))], pause=PAUSE, limits=(5.0, 1800.0))
    caps = []
    for size in ((80, 24),):
        keys = ScriptedKeys()
        caps.append(capture(arm, build(keys), keys, size, {"representative": {"person": "Alex"}}))
    text = caps[0].all_text()
    return {"ceiling": {"structure-on-request": "structure" in text.lower() and bool(__import__("re").search(r"structure \(|Tab hides", text)),
                        "spend-against-ceilings": "of $5.00" in text and "of 30:00" in text, "who-the-ai-acts-for": "for Alex" in text}}


import agents_scenarios as A  # noqa: E402
import feed_scenarios as F  # noqa: E402
import capabilities_scenarios as K  # noqa: E402

SCENARIOS = {**A.SCENARIOS, **F.SCENARIOS, "watch": watch, "steer": steer, "stop_resume": stop_resume, "approve": lambda arm: approval(arm, "y"), "refuse": lambda arm: approval(arm, "n"),
             "target": target, "plain": plain, "pasted_run": pasted_run, "real_run": real_run, "capabilities": K.in_process}
SECONDS = 30
SECONDS_OF = {**{name: 120 for name in A.SCENARIOS}, "capabilities": 300}    # the hierarchy scenarios walk in and out of helpers at three sizes (and four levels deep), each key given half a second to show


def run_scenario(arm: Any, name: str) -> Dict[str, Any]:
    """The scenario's result. An arm shown only through an external program (``presentation = "external"``) is not captured here: its screen checks are marked not run."""
    if presentation_of(arm) == "external":
        if getattr(arm, "external_scenarios", ""):       # an arm whose real client is run on a pseudo-terminal names the module that does it (opencode_external)
            import importlib
            return importlib.import_module(arm.external_scenarios).run_scenario(name)
        import external
        return external.run_scenario(name)
    done: Dict[str, Any] = {}

    def work() -> None:
        DRAWN.caps = []
        try:
            result = SCENARIOS[name](arm)
            if "labels-capitalised" not in result.get("checks", {}):        # revision 5: the capitalisation policy is read on every screen the scenario drew
                result = {**result, "checks": {**result.get("checks", {}), "labels-capitalised": C.combine([C.labels_capitalised(c) for c in DRAWN.caps])}}
            done["result"] = result
        except Exception as error:  # noqa: BLE001 -- an arm that cannot do the scenario fails it
            done["error"] = f"{type(error).__name__}: {error}"
    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(SECONDS_OF.get(name, SECONDS))
    if "result" in done:
        return done["result"]
    failed = {c: False for c in ALL_CHECKS if c in SCENARIO_CHECKS[name]}
    return {"checks": failed, "ceiling": {}, "note": done.get("error", "did not finish in time")}


SCENARIO_CHECKS = {**{name: (*checks, "labels-capitalised") for name, checks in {**A.SCENARIO_CHECKS}.items()}, **F.SCENARIO_CHECKS, "watch": ("each-update-once", "no-row-wider-than-the-terminal", "repaints-under-bound", "contrast-4.5", "current-step-visible", "closing-report-complete",
                             "first-output-within-a-second", "key-hints-present-and-whole"),
                   "steer": ("correction-sent-then-taken-up", "round-trip-steer"),
                   "stop_resume": ("stop-then-resume-keeps-work", "round-trip-stop", "round-trip-resume", "closing-report-complete"),
                   "approve": ("risky-step-waits-with-preview", "round-trip-approve"), "refuse": ("risky-step-waits-with-preview", "round-trip-refuse"),
                   "target": ("unavailable-control-shown",), "plain": ("plain-when-not-a-terminal",),
                   "capabilities": K.CHECKS,
                   "pasted_run": C.REVISION_2 +("closing-report-complete", "no-row-wider-than-the-terminal"),
                   "real_run": ("answer-once", "no-raw-markdown", "closing-report-complete", "no-row-wider-than-the-terminal")}
SCENARIO_CHECKS = {name: tuple(dict.fromkeys((*checks, "labels-capitalised"))) for name, checks in SCENARIO_CHECKS.items()}      # revision 5: every scenario is also read for capital letters
