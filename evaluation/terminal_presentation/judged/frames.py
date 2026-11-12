"""The six fixed frames of layer 2: start, mid_run, waiting, stopped, finished and narrow, taken from the scripted sessions of the presentation metric and written as text
grids a judge can read (a ruled box of the terminal's size, each row numbered). The frames are the arm's own screens, not a description of them. Free: no model."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scenarios as S  # noqa: E402
from screen import Capture, Snapshot  # noqa: E402

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import delegate, edit, read, report, stream_kit, turn, use  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys  # noqa: E402

FRAMES = ("start", "mid_run", "waiting", "stopped", "finished", "narrow")
NARROW = (40, 20)
WIDE = (80, 24)


def grid(rows: Tuple[str, ...], width: int, height: int) -> str:
    """The screen as a ruled text grid: every row padded to the width and numbered, so a judge can quote a row and a defect cannot hide in trailing blanks."""
    rows = tuple(rows[:height]) + ("",) * max(height - len(rows), 0)
    rule = "+" + "-" * width + "+"
    return "\n".join([rule] + [f"|{row[:width].ljust(width)}| {n:02d}" for n, row in enumerate(rows, 1)] + [rule])


def pick(cap: Capture, after: float, before: Optional[float] = None) -> Snapshot:
    chosen = [s for s in cap.snapshots if s.at >= after and (before is None or s.at < before) and any(r.strip() for r in s.rows)]
    return chosen[-1] if chosen else cap.final


def frames_of(arm: Any) -> Dict[str, str]:
    """The six frames of one arm as grids, from scripted sessions on a fake harness (no model)."""
    out: Dict[str, str] = {}
    w, h = WIDE
    keys = ScriptedKeys()
    cap = S.capture(arm, stream_kit(S.folder(), [turn(read("a.txt")), turn(edit("b.txt")), turn(delegate("write the tests", turn(edit("tests.txt"), report("tests done")))),
                                                  turn(edit("c.txt")), turn(report("All done."))], pause=0.3), keys, WIDE)
    first = next((s for s in cap.snapshots if any(r.strip() for r in s.rows)), cap.final)
    out["start"] = grid(first.rows, w, h)
    out["mid_run"] = grid(pick(cap, 0.7, 1.0).rows, w, h)
    out["finished"] = grid(cap.final.rows, w, h)

    keys = ScriptedKeys()
    keys.react = lambda event: threading.Timer(0.8, lambda: keys.press("line", "y")).start() if event.type == "waiting" else None
    cap = S.capture(arm, stream_kit(S.folder(), [turn(use("deploy", "release 1.0")), turn(report("Finished."))], pause=0.0), keys, WIDE)
    ask = next((at for at, e in cap.arrivals if e.type == "waiting"), 0.0)
    out["waiting"] = grid(pick(cap, ask, next((t for t, c, _ in cap.controls), None)).rows, w, h)

    keys = ScriptedKeys()
    cap = S.capture(arm, stream_kit(S.folder(), [turn(edit("one.txt")), turn(edit("two.txt"), hook=lambda: keys.press("esc")), turn(edit("three.txt"), report("All three."))], pause=0.2), keys, WIDE)
    out["stopped"] = grid(cap.final.rows, w, h)

    keys = ScriptedKeys()
    cap = S.capture(arm, stream_kit(S.folder(), [turn(read("a.txt")), turn(edit("b.txt")), turn(report("Done."))], pause=0.2), keys, NARROW)
    out["narrow"] = grid(pick(cap, 0.3, 0.6).rows, *NARROW)
    return out
