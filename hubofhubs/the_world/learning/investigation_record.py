"""The rules of an investigation record: the knowledge search standard of the ESOI library (``docs/reference/knowledge-search-standard.md``) as pure functions
and one dataclass, so Learning's arms, its metric and the stores all speak the same record. No model call, no network, no file written here.

An investigation is one piece of information gathering done to answer a question; its ``kind`` is review, trial, observation, interview or other, and Learning
does reviews. A review is a small systematic review sized to the decision it informs: a question and the decision, a method fixed and dated before the first
query, the exact queries with their dates and hit counts, screening with a count for each reason, items extracted and graded A to D, a synthesis of what is
known, contested and unknown, limitations, a decision for each candidate, what each item changed (the applied part) and the date to revisit. The record is two
tables, ``investigations.csv`` (one row per investigation) and ``investigation_items.csv`` (one row per kept item), with the columns of the library's standard;
``gaps`` lists what a record lacks for its size, as advice.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SIZES = ("quick", "standard", "full")
DECISIONS = ("adopt", "adapt", "build-on", "reject", "defer", "no-candidate")
KINDS = ("review", "trial", "observation", "interview", "other")
VERIFIED = ("opened", "cross-checked", "snippet", "not-opened", "observed")
REFRESH_DAYS = {"quick": 30, "standard": 90, "full": 180}     # when a review is redone, by size (a registry area keeps the registry's own 90)
GRACE_DAYS = {"quick": 7, "standard": 14, "full": 30}         # findings are applied, or marked not applied, within this many days
QUERIES = {"quick": 3, "standard": 5, "full": 8}               # the most queries the plan issues at each size (the standard's minimum is five for standard)
OPEN_LIMIT = {"quick": 3, "standard": 6, "full": 15}           # how many kept items are opened (read through the Science seat) to verify them; quick opens the top three, and an item whose page cannot be read stays a snippet
SNIPPET_CAP = "C"                                              # standard and full: an item read only as a snippet is graded no higher than this
SOURCE_KINDS = {"quick": ("web search", "opened pages"), "standard": ("web search", "scholarly search", "opened pages"), "full": ("web search", "scholarly search", "opened pages")}   # quick searches the web and opens its top three kept pages; standard and full also search scholarly sources and open more
COLUMNS = ["investigation_id", "kind", "intent_id", "experiment_id", "links", "question", "decision", "size", "protocol_date", "method", "criteria", "sources",
           "queries", "found", "screened_out", "kept", "observe", "change_my_mind", "stop", "done_on", "synthesis_known", "synthesis_contested",
           "synthesis_unknown", "limitations", "decisions", "refresh_on", "status"]
ITEM_COLUMNS = ["investigation_id", "item_id", "claim", "source", "source_date", "independent", "verified", "licence", "grade", "knowledge_id", "applied"]
MINIMUM = ("kind", "intent_id", "question", "decision", "size", "protocol_date", "method", "criteria", "sources", "queries", "done_on", "found",
           "screened_out", "kept", "limitations", "decisions", "refresh_on")
SYNTHESIS = ("synthesis_known", "synthesis_contested", "synthesis_unknown")
NEGATIVE = ("deprecated", "archived", "unmaintained", "abandoned", "end of life", "no longer maintained")
SEP = ";"


def choose_size(weight: Any) -> str:
    """The size of a review from the weight of its decision. ``weight`` is a size already, or a mapping: ``reversible_days`` (how long to undo it),
    ``reaches`` (solutions it touches), ``selects`` (it picks or changes an implementation, a metric, a prior or a registry area), ``dependency``
    (others rely on the result), ``outward`` (money, a licence, privacy, safety or a public claim), ``new_solution``. Hard to reverse, outward or a new
    solution is full; selecting, depended on, reaching several solutions or taking over a day to undo is standard; else quick. When two fit, the larger."""
    if isinstance(weight, str) and weight in SIZES:
        return weight
    w: Mapping[str, Any] = weight or {}
    days = float(w.get("reversible_days", 0) or 0)
    if w.get("outward") or w.get("new_solution") or days > 7 or (w.get("dependency") and days > 1):
        return "full"
    if w.get("selects") or w.get("dependency") or int(w.get("reaches", 1) or 1) > 1 or days > 1:
        return "standard"
    return "quick"


def grade(sources: Sequence[Mapping[str, Any]]) -> str:
    """A to D for one claim from the sources that support it, by the library's rule: a vendor or maintainer alone is D; no independent source is C at most;
    one independent source is B at most; two independent sources that agree make A. A source is ``independent`` (yes, no, unknown) and may say ``relation``
    (vendor, maintainer, other)."""
    if not sources:
        return "D"
    if all(str(s.get("relation", "")) in ("vendor", "maintainer") or s.get("independent") == "no" for s in sources):
        return "D"
    independent = [s for s in sources if s.get("independent") == "yes"]
    if len(independent) >= 2:
        return "A"
    return "B" if independent else "C"


def cap_grade(grade: str, verified: str, size: str) -> str:
    """The grade an item may carry given how it was read: at standard and full size an item read only as a snippet (or not opened) is C at most, whatever its
    sources say; opened and cross-checked items keep the rule's grade. Quick keeps the rule's grade, opens its top three pages, and says in its limitations which items it read as snippets only."""
    if size in ("standard", "full") and verified in ("snippet", "not-opened") and grade in ("A", "B"):
        return SNIPPET_CAP
    return grade


def refresh_on(done: str, size: str, days: Optional[int] = None) -> str:
    return (date.fromisoformat(done) + timedelta(days=days or REFRESH_DAYS[size])).isoformat()


def counted(entries: Sequence[str]) -> Optional[int]:
    total = 0
    for entry in entries:
        head = entry.split(" ", 1)[0]
        if not head.isdigit() or " " not in entry:
            return None
        total += int(head)
    return total


def parts(cell: str) -> List[str]:
    return [p.strip() for p in (cell or "").split(SEP) if p.strip()]


@dataclass
class Investigation:
    """One investigation (a review): the row of ``investigations.csv`` (``row``), the rows of ``investigation_items.csv`` (``items``), the per-item applied part, and what the search log held."""
    row: Dict[str, str]
    items: List[Dict[str, str]] = field(default_factory=list)
    protocol: Dict[str, Any] = field(default_factory=dict)
    log: List[Dict[str, Any]] = field(default_factory=list)       # each query with its source, date and hit count
    reasons: Dict[str, int] = field(default_factory=dict)         # screening: reason -> count
    applied: List[Dict[str, str]] = field(default_factory=list)   # item id -> what it changed or why not

    def to_dict(self) -> Dict[str, Any]:
        return {"investigation": self.row, "items": self.items, "applied": self.applied, "protocol": self.protocol, "queries": self.log,
                "screened_out": self.reasons, "gaps": gaps(self.row, self.items)}


def gaps(row: Mapping[str, str], items: Sequence[Mapping[str, str]], on: Optional[date] = None) -> List[str]:
    """What an investigation record lacks against the standard for its size (advice, never a failure)."""
    out: List[str] = []
    size = (row.get("size") or "").strip()
    if size not in SIZES:
        out.append(f"size {size!r} is not one of {', '.join(SIZES)}")
    if (row.get("kind") or "") not in KINDS:
        out.append("kind is not one of " + ", ".join(KINDS))
    out += [f"has no {c}" for c in MINIMUM if not (row.get(c) or "").strip()]
    if not any(link.startswith("solution:") for link in parts(row.get("links", ""))):
        out.append("links name no solution (an investigation is filed under at least one solution, up to the top solution); older rows are still read")
    if size in ("standard", "full"):
        out += [f"has no {c}" for c in SYNTHESIS if not (row.get(c) or "").strip()]
    if row.get("protocol_date") and row.get("done_on") and row["protocol_date"] > row["done_on"]:
        out.append("protocol_date is after done_on")
    found, kept = (row.get("found") or "").strip(), (row.get("kept") or "").strip()
    cut = counted(parts(row.get("screened_out", "")))
    if found.isdigit() and kept.isdigit() and cut is not None and int(found) - cut != int(kept):
        out.append(f"found {found} less screened out {cut} is not kept {kept}")
    for entry in parts(row.get("decisions", "")):
        pieces = [p.strip() for p in entry.split(":", 2)]
        if len(pieces) < 3 or pieces[1] not in DECISIONS or not pieces[2]:
            out.append(f"decision {entry!r} reads `candidate: verb: reason`")
    if kept.isdigit() and int(kept) != len(items):
        out.append(f"kept {kept} but {len(items)} item(s)")
    for item in items:
        if item.get("grade") not in ("A", "B", "C", "D"):
            out.append(f"item {item.get('item_id')} has no grade")
        if not (item.get("applied") or "").strip() and on and row.get("done_on") and (on - date.fromisoformat(row["done_on"])).days > GRACE_DAYS.get(size, 14):
            out.append(f"item {item.get('item_id')} is neither applied nor marked not-applied")
    return out
