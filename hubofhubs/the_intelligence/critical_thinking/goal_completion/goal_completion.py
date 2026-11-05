"""Goal Completion: says whether a goal's condition was met against its done-standard, as a mapping with ``met`` and ``reason``.

``evidence_standard`` reads two things and no prose judgment: the outcome's declared coverage (a ``coverage`` record from the worker's own
bookkeeping, through ``done_evidence``: a set that was not fully processed is not met), and the done-standard's requirements (each a
checkable phrase that the outcome's text must contain). An outcome that is empty, or that says a step was refused, is not met. Pure
functions, no model call. Standard library plus the hub and ``esoi``."""
from typing import Any, List, Mapping

from esoi import implementation

from hubofhubs.the_intelligence.critical_thinking.goal_completion.done_evidence import clean_requirements, coverage_gap, render_coverage_line


def outcome_text(outcome: Any) -> str:
    if isinstance(outcome, Mapping):
        return str(outcome.get("text") or outcome.get("output") or "")
    return str(outcome or "")


def requirements_of(done_standard: str) -> List[str]:
    """The requirements a done-standard states: its ``;``-separated clauses after a ``must contain`` or ``includes`` (checkable phrases), else none."""
    for marker in ("must contain", "includes", "must include"):
        if marker in done_standard.lower():
            tail = done_standard[done_standard.lower().index(marker) + len(marker):]
            return clean_requirements([part.strip(" .:") for part in tail.split(";")])
    return []


@implementation("goal-completion", "evidence_standard")
class EvidenceStandard:
    """Met when the outcome says something, declares no coverage gap, was not refused, and holds every requirement of the done-standard."""
    REQUIRES = ()     # pure functions

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]:
        text = outcome_text(outcome)
        if isinstance(outcome, Mapping) and outcome.get("refused"):
            return {"met": False, "reason": f"the work was refused: {outcome['refused']}"}
        if not text.strip():
            return {"met": False, "reason": "the outcome is empty"}
        raw = outcome.get("coverage") if isinstance(outcome, Mapping) else None
        if coverage_gap(raw) is not None:
            return {"met": False, "reason": render_coverage_line(raw)}
        missing = [r for r in requirements_of(done_standard) if r.lower() not in text.lower()]
        if missing:
            return {"met": False, "reason": "the outcome does not hold: " + "; ".join(missing)}
        return {"met": True, "reason": "the outcome is present, complete as declared, and holds every requirement"}


@implementation("goal-completion", "nonempty")
class NonEmpty:
    """Met when the outcome is not empty: what a flow with no completion check implies. The bound the evidence standard has to beat."""
    REQUIRES = ()     # nothing

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]:
        text = outcome_text(outcome)
        return {"met": bool(text.strip()), "reason": "the outcome is not empty" if text.strip() else "the outcome is empty"}
