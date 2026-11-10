"""What a repeated run on one solution needs to remember and to frame its worker with, with no model call: which requirement each unit failed, whether a
rewritten unit is better than the one it replaces, and the labelled frame of the solution (its approach, next unmet milestone and disadvantages) a worker
is briefed with.

Role: a worker that makes a set of units (one script per video, one entry per option) against a list of requirements is measured by a separate check, and
the next run on the same work should not repeat the last run's failures. ``unmet_by_unit`` turns the check's verdicts into the requirement each unit fails (a
count alone tells the next run nothing); ``keep_better`` lets a rewrite of a unit replace it only when it meets strictly more requirements (the same
"never keep a lower score" rule as ``solution_passes.depth.build_out``, counted in requirements met because that is what the check returns per unit);
``solution_frame`` is the labelled lines that put the worker inside the solution's own records instead of only its rubric. The check itself (``meets``)
is the caller's: a stub in a test, a separate scoring call in a deployment.
"""
from __future__ import annotations

from typing import Any, Callable, List, Mapping, Sequence, Tuple

FRAME_LABELS = (
    ("approach", "Approach"),
    ("next_milestone", "Next unmet milestone"),
    ("metric_disadvantages", "What the metric cannot see"),
    ("implementation_disadvantages", "Disadvantages of the implementation in use"),
    ("last_value", "Last measured value"),
    ("unmet", "Unmet from the last measure"),
)
FRAME_CHARS = 1200      # a frame is a few lines above the records, not a second copy of them


def unmet_by_unit(units: Sequence[Any], requirements: Sequence[str], meets: Callable[[str, Any], bool]) -> List[List[str]]:
    """Per unit (in order), the requirements it does not meet, in the order of ``requirements``; an empty list for a unit that meets them all.
    ``meets(requirement, unit)`` is called once for each pair."""
    return [[r for r in requirements if not meets(r, unit)] for unit in units]


def met_count(unit: Any, requirements: Sequence[str], meets: Callable[[str, Any], bool]) -> int:
    return sum(1 for r in requirements if meets(r, unit))


def keep_better(old_unit: Any, new_unit: Any, requirements: Sequence[str], meets: Callable[[str, Any], bool]) -> Tuple[Any, bool]:
    """``(unit, kept_new)``: ``new_unit`` only when it meets strictly more of ``requirements`` than ``old_unit``; otherwise ``old_unit``, so a rewrite
    that is equal or worse is never kept. With no requirements nothing can be measured, so the old unit stays."""
    if not requirements:
        return old_unit, False
    better = met_count(new_unit, requirements, meets) > met_count(old_unit, requirements, meets)
    return (new_unit, True) if better else (old_unit, False)


def solution_frame(fields: Mapping[str, Any], chars: int = FRAME_CHARS) -> str:
    """Labelled lines for whichever of ``approach``, ``next_milestone``, ``metric_disadvantages``, ``implementation_disadvantages``, ``last_value`` and
    ``unmet`` (a string or a list of strings) are present and non-empty, in that order, cut at ``chars`` on a line boundary (a line longer than the room
    is shortened); "" when none is present."""
    lines: List[str] = []
    for key, label in FRAME_LABELS:
        value = fields.get(key)
        parts = [str(v).strip() for v in value] if isinstance(value, (list, tuple)) else [str(value or "").strip()]
        text = "; ".join(" ".join(p.split()) for p in parts if p)
        if text:
            lines.append(f"{label}: {text}")
    out: List[str] = []
    room = chars
    for line in lines:
        if len(line) + 1 > room:
            if room > 40:
                out.append(line[:room - 2].rstrip() + "...")
            break
        out.append(line)
        room -= len(line) + 1
    return "\n".join(out)
