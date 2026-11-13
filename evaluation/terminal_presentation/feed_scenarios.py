"""The feed and stop scenarios of the presentation metric (revision 5, 2026-11-12), from a real run of the full-screen views: a made-up folder, a scripted event stream (no model) with the
things that run showed, drawn at every size and read back from the screen like every other scenario.

* ``feed_noise``: the agent's own task-list tools, reads of files that are not there, commands that did not work (one repeated), a helper that works for a while with a long name, then the
  answer. Judged by ``no-bookkeeping-tool-lines``, ``failed-command-one-muted-line`` and ``footer-clean-at-every-width`` (the footer is read while the helper runs, at 56, 80 and 120 columns).
* ``ceiling_stop``: the same kind of run stopped at its spend ceiling while a helper was working. Judged by ``ceiling-stop-said-once``.

``labels-capitalised`` is not a scenario of its own: ``scenarios.run_scenario`` runs it over every screen every scenario drew. Standard library and the hub only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import checks as C
from screen import Capture

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import (
    bookkeeping, delegate, edit, fail_read, fail_run, hard_stop, read, report, run, search, stream_kit, turn)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys

#: a made-up helper whose name is long enough to be cut at the narrowest width
HELPER = "Find one interesting finding in the garden notes. Then summarise what it shows."
PAUSE = 0.25
NOT_DRIVEN = ("revision 5 (2026-11-12): these checks read the hub's own words and rows; a third-party client draws its own, so they are listed as not run and are neither a pass nor a fail")


def script(stop: bool) -> List[Any]:
    helper = delegate(HELPER, turn(read("notes/one.md"), read("notes/two.md"), bookkeeping("TaskUpdate"), fail_run("ls -la /made/up/folder"), search("seeds"), read("notes/three.md")))
    beats = [bookkeeping("TaskCreate"), bookkeeping("TaskCreate"), bookkeeping("TaskCreate"), read("notes/a.md"), fail_read("notes/missing-one.md"), fail_read("notes/missing-two.md"),
             fail_run('cd /made/up; grep -rhoiE "(because|pattern)" . | sort | uniq -c'), fail_run("for f in a b c; do echo $f; done"), fail_run("for f in a b c; do echo $f; done"),
             run("ls"), helper, edit("summary.txt")]
    return [turn(*beats, *([hard_stop("spend")] if stop else [report("Here is what the notes show.")]))]


def captures(arm: Any, stop: bool) -> List[Capture]:
    import scenarios as S
    caps = []
    for size in S.SIZES:
        keys = ScriptedKeys()
        kit = stream_kit(S.folder(), script(stop), pause=PAUSE, limits=(20.0, 14400.0))
        caps.append(S.capture(arm, kit, keys, size))
    return caps


def feed_noise(arm: Any) -> Dict[str, Any]:
    import scenarios as S
    caps = captures(arm, False)
    return {"checks": {"no-bookkeeping-tool-lines": S.over(caps, C.no_bookkeeping_lines), "failed-command-one-muted-line": S.over(caps, C.failed_command_muted),
                       "footer-clean-at-every-width": S.over(caps, C.footer_clean)}}


def ceiling_stop(arm: Any) -> Dict[str, Any]:
    import scenarios as S
    caps = captures(arm, True)
    return {"checks": {"ceiling-stop-said-once": S.over(caps, C.ceiling_stop_said_once), "closing-report-complete": S.over(caps, C.closing_report_complete)}}


SCENARIOS = {"feed_noise": feed_noise, "ceiling_stop": ceiling_stop}
SCENARIO_CHECKS = {"feed_noise": ("no-bookkeeping-tool-lines", "failed-command-one-muted-line", "footer-clean-at-every-width", "labels-capitalised"),
                   "ceiling_stop": ("ceiling-stop-said-once", "closing-report-complete", "labels-capitalised")}
