"""done_evidence -- the STRUCTURAL half of "finish the job before reporting".

A goal that covers a SET ("every entry", "all 344 records") is not met by a reply that merely reads
well: it is met when the set was processed. Judging that from the reply's prose was the whole
enforcement, so a run that read 200 of 344 rows could pass whenever its own words did not admit it.
This module makes the gap a fact the loop can act on, with no model call and no reading of any
text (the same shape as ``sufficiency``: a structural declaration the loop gates on):

  * A run declares its COVERAGE as plain data, ``DeepResult.coverage``::

        {"processed": 200, "total": 344, "unit": "entries",
         "complete": False, "capped": True,
         "remaining": 144, "next_skip": 200,
         "reads": [...], "withheld": ...}

    Every key is optional. The runner fills it from its OWN bookkeeping (the data call that
    returned a capped page, a count it made), never from the words of its output.
  * ``coverage_gap`` turns that declaration into a gap, or None when nothing is missing or nothing
    is declared (an undeclared coverage never blocks anything).
  * ``continue_decision`` is the stop/continue rule on the gap: continue while there is room and
    the last attempt moved the numbers; otherwise stop and say so honestly.
  * ``render_requirements``, ``render_coverage_line`` and ``render_continue_plan`` are the code-written
    lines a reader sees, so the coverage statement never depends on what a model chose to say.

Pure functions and small dataclasses. Nothing here knows a consumer, a database or an organization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

#: The longest a single requirement may be, and how many are kept: checkable items, not an essay.
MAX_REQUIREMENTS = 4
MAX_REQUIREMENT_CHARS = 200

#: The verdicts of ``continue_decision``.
CONTINUE = "continue"
STOP_COMPLETE = "complete"
STOP_NO_PROGRESS = "no_progress"
STOP_NO_BUDGET = "no_budget"


def _whole(value: Any) -> Optional[int]:
    """A non-negative integer, or None for anything else (a bool, a float, a string, a negative)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


@dataclass(frozen=True)
class CoverageRecord:
    """A runner's declared coverage of a set, parsed. ``total`` None means the size is not known."""
    processed: int = 0
    total: Optional[int] = None
    unit: str = "records"
    complete: Optional[bool] = None
    capped: bool = False
    remaining: Optional[int] = None
    next_skip: Optional[int] = None
    reads: Tuple[Any, ...] = ()
    withheld: Any = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"processed": self.processed, "total": self.total, "unit": self.unit,
                               "complete": self.complete, "capped": self.capped,
                               "remaining": self.remaining, "next_skip": self.next_skip}
        if self.reads:
            out["reads"] = list(self.reads)
        if self.withheld is not None:
            out["withheld"] = self.withheld
        return out


def parse_coverage(raw: Any) -> Optional[CoverageRecord]:
    """The declared coverage as a ``CoverageRecord``, or None when nothing usable was declared.

    Tolerant on purpose: a runner on an older shape, a missing key or a wrong type degrades to "not
    declared" for that key, never an exception and never a guess. Needs at least a ``processed``
    count to mean anything.
    """
    if isinstance(raw, CoverageRecord):
        return raw
    if not isinstance(raw, dict):
        return None
    processed = _whole(raw.get("processed"))
    if processed is None:
        return None
    total = _whole(raw.get("total"))
    remaining = _whole(raw.get("remaining"))
    if remaining is None and total is not None:
        remaining = max(0, total - processed)
    unit = raw.get("unit")
    reads = raw.get("reads")
    return CoverageRecord(
        processed=processed, total=total,
        unit=unit.strip() if isinstance(unit, str) and unit.strip() else "records",
        complete=raw["complete"] if isinstance(raw.get("complete"), bool) else None,
        capped=raw.get("capped") is True, remaining=remaining,
        next_skip=_whole(raw.get("next_skip")),
        reads=tuple(reads) if isinstance(reads, (list, tuple)) else (),
        withheld=raw.get("withheld"))


@dataclass(frozen=True)
class CoverageGap:
    """What is missing from a declared set. ``remaining`` None means a capped read of unknown size."""
    processed: int
    total: Optional[int]
    remaining: Optional[int]
    unit: str
    next_skip: Optional[int]


def coverage_gap(raw: Any) -> Optional[CoverageGap]:
    """The gap in a declared coverage, or None when it is complete or nothing was declared.

    An explicit ``complete`` wins. Otherwise a known ``total`` above ``processed`` is a gap, and a
    ``capped`` read of unknown size is a gap too (the source said there is more than it returned).
    """
    record = parse_coverage(raw)
    if record is None or record.complete is True:
        return None
    if record.total is not None:
        if record.processed >= record.total:
            return None
        return CoverageGap(record.processed, record.total, record.total - record.processed,
                           record.unit, record.next_skip)
    if record.complete is False or record.capped:
        return CoverageGap(record.processed, None, record.remaining, record.unit, record.next_skip)
    return None


def coverage_progress(previous: Any, current: Any) -> bool:
    """True when ``current`` covers more than ``previous`` (or there was no previous record).

    The difference between a long job that is advancing and a runaway that repeats itself.
    """
    now = parse_coverage(current)
    if now is None:
        return False
    before = parse_coverage(previous)
    if before is None or now.processed > before.processed:
        return True
    # A run that reports only its own pages still advances when its resume point does.
    return now.next_skip is not None and (before.next_skip is None or now.next_skip > before.next_skip)


def continue_decision(gap: Optional[CoverageGap], *, attempts_left: int,
                      budget_left: Optional[int] = None, progressed: bool = True) -> Tuple[str, str]:
    """``(verdict, why)``: whether to run again on a coverage gap.

    ``attempts_left`` counts the attempts the loop may still make, ``budget_left`` the tokens (None =
    unbounded), ``progressed`` whether the attempt just made covered more than the one before. A
    complete coverage stops with ``complete``; no room stops with ``no_budget``; room but no movement
    stops with ``no_progress`` (repeating the same attempt would only repeat the same gap).
    """
    if gap is None:
        return STOP_COMPLETE, "the declared coverage is complete"
    if attempts_left <= 0 or (budget_left is not None and budget_left <= 0):
        return STOP_NO_BUDGET, "the work budget is spent"
    if not progressed:
        return STOP_NO_PROGRESS, "the last attempt covered nothing more"
    return CONTINUE, "coverage is incomplete and the last attempt advanced it"


def clean_requirements(raw: Any) -> List[str]:
    """A planner's ``done_evidence`` as at most ``MAX_REQUIREMENTS`` short non-empty strings."""
    if not isinstance(raw, (list, tuple)):
        return []
    out: List[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(" ".join(item.split())[:MAX_REQUIREMENT_CHARS])
        if len(out) >= MAX_REQUIREMENTS:
            break
    return out


def render_requirements(items: Iterable[str]) -> str:
    """The requirements as a numbered block, or "" when there are none."""
    lines = [f"  R{i}. {text}" for i, text in enumerate(clean_requirements(list(items)), 1)]
    return "\n".join(lines)


def _count(value: Optional[int], unit: str) -> str:
    return f"{value:,} {unit}" if value is not None else f"an unknown number of {unit}"


def render_coverage_line(raw: Any) -> str:
    """One code-written sentence stating coverage, or "" when none was declared."""
    record = parse_coverage(raw)
    if record is None:
        return ""
    gap = coverage_gap(record)
    if record.total is not None and gap is None:
        return f"Coverage: {record.total:,} of {record.total:,} {record.unit} processed."
    if record.total is not None:
        return (f"Coverage: {record.processed:,} of {record.total:,} {record.unit} processed "
                f"({record.total - record.processed:,} not yet covered).")
    if gap is not None:
        return f"Coverage: {record.processed:,} {record.unit} processed; the source holds more."
    return f"Coverage: {record.processed:,} {record.unit} processed."


def render_continue_plan(raw: Any) -> str:
    """How to pick the rest up, from the declared gap, or "" when nothing is left."""
    gap = coverage_gap(raw)
    if gap is None:
        return ""
    where = f" from {gap.unit} {gap.next_skip + 1:,}" if gap.next_skip is not None else ""
    rest = _count(gap.remaining, gap.unit)
    return f"To cover the rest ({rest}), continue{where}."


def interim_data(raw: Any, **extra: Any) -> Dict[str, Any]:
    """The ``data`` of an ``EVENT_INTERIM`` event: ``{"final": False, "coverage": {...}|None, ...}``."""
    record = parse_coverage(raw)
    data: Dict[str, Any] = {"final": False, "coverage": record.to_dict() if record else None}
    data.update(extra)
    return data


# --- Measuring an AI increment ------------------------------------------------------------------------------------------------------------------------
#
# A progress turn shows a measured before and after. ``measure`` scores an increment's artifact against the increment's requirements by a judge the
# CALLER gives (a check that is not the model that wrote the artifact: Decision Check views, or Response Quality), counts evidence coverage from structured
# answers, or takes a reader's value. An empty or missing artifact scores 0; a kept earlier version is scored again the same way, so before and after are
# one measure against itself. A simulation reading is labelled as one.

MEASURE_METHODS = ("read", "rubric", "evidence", "quality_score", "simulation")


@dataclass(frozen=True)
class Reading:
    """One measured value of an increment: ``value`` out of ``total`` (None when there is none), ``as_of`` the day, ``source`` what was measured,
    ``evidence_ref`` where the artifact is kept, ``method`` how it was measured, ``simulated`` for a simulation, ``detail`` per-part results."""
    measure_id: str
    value: Optional[float]
    as_of: str = ""
    source: str = ""
    evidence_ref: str = ""
    method: str = ""
    total: Optional[int] = None
    simulated: bool = False
    detail: Tuple[Any, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"measure_id": self.measure_id, "value": self.value, "as_of": self.as_of, "source": self.source, "evidence_ref": self.evidence_ref,
                "method": self.method, "total": self.total, "simulated": self.simulated, "detail": list(self.detail)}


def parts_of(artifact: Any) -> List[str]:
    """The parts of an artifact a rubric is applied to: ``{"parts": [...]}`` as listed, a list as is, a text as one part; empty text is no part."""
    if isinstance(artifact, dict):
        artifact = artifact.get("parts") if "parts" in artifact else artifact.get("text")
    if isinstance(artifact, (list, tuple)):
        return [str(p) for p in artifact if str(p or "").strip()]
    return [str(artifact)] if str(artifact or "").strip() else []


def rubric_coverage(requirements: Iterable[str], artifact: Any, judge: Any) -> Tuple[int, List[Dict[str, Any]]]:
    """``(parts meeting every requirement, per-part detail)``. ``judge(requirement, part) -> bool`` is the caller's independent check; a part with no
    requirement to meet counts as meeting none (a rubric must exist to count)."""
    items = [r for r in requirements if str(r or "").strip()]
    met, detail = 0, []
    for k, part in enumerate(parts_of(artifact)):
        results = [bool(judge(r, part)) for r in items] if items else []
        whole = bool(results) and all(results)
        met += whole
        detail.append({"part": k + 1, "met": whole, "items": results})
    return met, detail


def evidence_coverage(artifact: Any) -> Tuple[int, Optional[int]]:
    """``(questions answered with a cited source, questions the decision needs)`` from ``{"questions": [{"answer": ..., "source": ...}, ...]}``."""
    questions = artifact.get("questions") if isinstance(artifact, dict) else None
    if not isinstance(questions, list):
        return 0, None
    answered = sum(1 for q in questions if isinstance(q, dict) and str(q.get("answer") or "").strip() and str(q.get("source") or "").strip())
    return answered, len(questions)


def measure(increment: Any, artifact: Any, judge: Any = None, reader: Any = None, today: str = "", evidence_ref: str = "",
            total: Optional[int] = None) -> Reading:
    """The increment's measure of ``artifact`` now: ``rubric`` (parts meeting every requirement, judged by ``judge``), ``evidence`` (questions answered with
    a cited source), ``read`` (``reader()`` returning ``{"value", "as_of", "source"}``), ``quality_score`` (``judge(None, text) -> float``) or
    ``simulation`` (a reader's value, labelled simulated). ``increment`` is an ``Increment`` or its mapping. Never raises for a missing artifact: it is 0."""
    data = increment.to_dict() if hasattr(increment, "to_dict") else dict(increment or {})
    method = str(data.get("method") or "rubric")
    measure_id = str(data.get("measure_id") or "")
    if method == "read" or method == "simulation":
        got = dict(reader() or {}) if reader is not None else {}
        value = got.get("value")
        try:
            value = float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            value = None
        return Reading(measure_id, value, str(got.get("as_of") or today), str(got.get("source") or ""), evidence_ref, method, total,
                       simulated=method == "simulation")
    if method == "evidence":
        answered, needed = evidence_coverage(artifact)
        return Reading(measure_id, float(answered), today, "evidence coverage", evidence_ref, method, needed if needed is not None else total)
    if method == "quality_score":
        text = "\n".join(parts_of(artifact))
        score = float(judge(None, text)) if (judge is not None and text) else 0.0
        return Reading(measure_id, score, today, "quality score", evidence_ref, method, total)
    if judge is None:
        raise ValueError("a rubric measure needs a judge that is not the writer of the artifact")
    met, detail = rubric_coverage(data.get("requirements") or [], artifact, judge)
    return Reading(measure_id, float(met), today, "rubric", evidence_ref, "rubric", total, detail=tuple(detail))
