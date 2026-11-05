"""One step of a flow: a call to the entry point of a solution, and an honest account of what came back.

A composition arm takes the solutions it uses as typed needs (``Lazy[Seat]``), and ``take`` calls the entry point that the seat declares
with ``@solution(id, entry=...)``, the same method ``hubofhubs.run(id, ...)`` calls. A solution that has no arm yet, or whose arm cannot be
built here (a missing key, an install), is recorded as ``pending`` with the reason and nothing is made up in its place; a step that had
nothing to act on is ``skipped``. Standard library plus ``esoi``; nothing here reads the environment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi.assemble import AssemblyError
from esoi.entry import declared

DONE, PENDING, SKIPPED = "done", "pending", "skipped"
NO_ARM = "no arm yet"


@dataclass(frozen=True)
class Step:
    """One solution's part in a flow: ``status`` is done (``output`` is what it returned), pending (``reason`` says why it could not run) or skipped."""
    solution: str
    status: str
    output: Any = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out = self.output
        steps = out.get("steps") if isinstance(out, Mapping) else None
        row: Dict[str, Any] = {"solution": self.solution, "status": self.status}
        if self.reason:
            row["reason"] = self.reason
        if steps:
            row["steps"] = list(steps)
        return row


def pending_reason(error: Exception) -> str:
    """The first line of why a seat could not be built: ``no arm yet`` when its record names no implementation, else the line esoi gave."""
    text = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
    lowered = text.lower()
    if "no arm" in lowered or "no implementation" in lowered or "pass your own object" in lowered or "has no" in lowered:
        return NO_ARM
    return text


def take(part: Any, solution_id: str, method: str = "", **arguments: Any) -> Step:
    """Call the entry point of ``solution_id`` on ``part`` (or the named ``method`` of it) with ``arguments`` and return the step."""
    from hubofhubs.the_self.assembler.resolution import HUB  # late: the hub's records and seats load only when a flow runs
    if not method:
        found = declared(HUB, solution_id)
        method = found.entry if found is not None and found.entry else ""
    try:
        call = getattr(part, method)
    except AssemblyError as error:
        return Step(solution_id, PENDING, reason=pending_reason(error))
    return Step(solution_id, DONE, call(**arguments))


def skipped(solution_id: str, reason: str) -> Step:
    return Step(solution_id, SKIPPED, reason=reason)


def listing(steps: Sequence[Step]) -> List[Dict[str, Any]]:
    return [s.to_dict() for s in steps]


def done(found: Step) -> Any:
    """What a step returned, or None when it did not run."""
    return found.output if found.status == DONE else None
