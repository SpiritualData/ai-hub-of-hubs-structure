"""The calibration set of layer 2: clean frames of the reference terminal (frozen in ``calibration_frames.json``) and the same frames with one defect injected each, every
defect tied to the checklist item it breaks. The clean frame of a pair is checked to carry the feature the defect removes (``present``), so a defect is never injected into a
frame that did not have it. The set measures the judge (``judge.calibrate``); it says nothing about any arm. The item ``fits-the-narrow-terminal`` has no pair: a grid cannot
be made wider than the terminal, so it is left to layer 1 (``no-row-wider-than-the-terminal``)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "calibration_frames.json"
ROW = re.compile(r"^\|(.*)\|\s*(\d+)$")


def rows_of(grid: str) -> List[str]:
    return grid.splitlines()


def blank(grid: str, pattern: str) -> str:
    """The grid with every row that matches ``pattern`` emptied."""
    out = []
    for line in rows_of(grid):
        m = ROW.match(line)
        out.append(f"|{' ' * len(m.group(1))}| {m.group(2)}" if m and re.search(pattern, m.group(1)) else line)
    return "\n".join(out)


def strip_text(grid: str, pattern: str) -> str:
    """The grid with the text that matches ``pattern`` taken out of its row."""
    out = []
    for line in rows_of(grid):
        m = ROW.match(line)
        if m and re.search(pattern, m.group(1)):
            body = re.sub(pattern, "", m.group(1)).ljust(len(m.group(1)))
            out.append(f"|{body}| {m.group(2)}")
        else:
            out.append(line)
    return "\n".join(out)


def repeat(grid: str, pattern: str) -> str:
    """The grid with the first matching row copied into the next empty row (the same update shown twice)."""
    lines, source = rows_of(grid), None
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if m and source is None and re.search(pattern, m.group(1)):
            source = (i, m.group(1))
    if source is None:
        return grid
    for i in range(source[0] + 1, len(lines)):
        m = ROW.match(lines[i])
        if m and not m.group(1).strip():
            lines[i] = f"|{source[1]}| {m.group(2)}"
            break
    return "\n".join(lines)


def present(grid: str, pattern: str) -> bool:
    return any(re.search(pattern, m.group(1)) for m in map(ROW.match, rows_of(grid)) if m)


#: id, frame, checklist item, the pattern of the feature the clean frame carries, and how it is removed
DEFECTS: List[Tuple[str, str, str, str, Callable[[str], str]]] = [
    ("no-key-hints", "mid_run", "usable-keys-are-shown", r"\bEsc\b", lambda g: blank(g, r"\bEsc\b")),
    ("no-stop-hint", "mid_run", "stop-is-shown", r"\bEsc\b.*stop", lambda g: strip_text(g, r"Esc stop \| ")),
    ("repeated-row", "mid_run", "no-update-twice", r"edit\s+b\.txt", lambda g: repeat(g, r"edit\s+b\.txt")),
    ("repeated-row-finished", "finished", "no-update-twice", r"Changed \(", lambda g: repeat(g, r"Changed \(")),
    ("no-status-line", "mid_run", "shows-time-or-cost", r"\d:\d\d \|", lambda g: blank(g, r"\d:\d\d \|")),
    ("no-goal", "start", "start-names-the-goal", r"goal: ", lambda g: blank(g, r"goal: ")),
    ("no-preview", "waiting", "waiting-shows-what-will-change", r"will change", lambda g: blank(g, r"will change")),
    ("no-answer-keys", "waiting", "waiting-shows-how-to-answer", r"\[y\] approve", lambda g: blank(strip_text(g, r"\[y\] approve\s+\[n\] refuse"), r"y approve \| n refuse")),
    ("no-outcome", "finished", "outcome-in-a-plain-word", r"goal was met", lambda g: blank(g, r"goal was met")),
    ("no-changed-files", "finished", "changed-files-listed", r"Changed \(", lambda g: blank(g, r"Changed \(")),
    ("no-resume-way", "stopped", "stopped-says-kept-and-how-to-continue", r"resume", lambda g: blank(g, r"resume|continue later")),
    ("no-helper-row", "finished", "helpers-show-who-they-are", r"`-|└─", lambda g: blank(g, r"`-|└─")),
]


def build(frames: Dict[str, str]) -> List[Dict[str, Any]]:
    """The pairs for the frames of the reference arm; a defect whose feature the clean frame lacks is left out and named."""
    cases = []
    for name, frame, item, feature, remove in DEFECTS:
        clean = frames[frame]
        if present(clean, feature):
            cases.append({"id": name, "frame": frame, "item": item, "clean": clean, "defective": remove(clean)})
    return cases


def load_calibration() -> List[Dict[str, Any]]:
    return json.loads(FROZEN.read_text())["cases"]
