"""Pursuing an unmet goal, a step of the Critical Thinking composition (``pursue``): what happens to a draft whose goal condition is unmet.

It checks the draft (through the check it is given, else Goal Completion) and, while the condition is unmet and read-only means
remain untried, offers them to ``attempt`` and checks again, within a budget: ``max_replans`` rounds and ``wall_seconds`` in all. Work estimated
longer than ``inline_seconds`` is not made to wait: the work either continues inline or, when the budget says a ``background`` exists, is returned as the plan for
that follow-up. A write is never offered, and an attempt that reports one is discarded and recorded. No line is added to the response in any outcome (no "still working",
no list of what was tried, no "could not confirm"): the response says what it holds and the reply's own grounding says what it lacks. The result's ``tried`` and the checker's
own words (``missing``) are kept for logs and never put in a response. Every decision reads structured facts (the verdict's boolean, the means, the budget, what ``attempt``
returned), never the words of a response. A draft whose structured outcome is a question to the person (the check's ``awaiting_person`` flag) is a
terminal, satisfied state: the goal condition of a cut-off or ambiguous message is that the person supplies the missing piece, so nothing is pursued,
announced or queued and no line is added. Standard library plus the hub
and ``esoi``."""
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_self.steps import done, take

DEFAULT_BUDGET: Dict[str, Any] = {"max_replans": 2, "wall_seconds": 90.0, "inline_seconds": 30.0, "background": False}
MET, MET_AFTER_REPLAN, UNMET_REPORTED, CONTINUING, UNMET_SENT_AS_IS = "met", "met_after_replan", "unmet_reported", "continuing", "unmet_sent_as_is"
AWAITING_PERSON = "awaiting_person"
REFUSED_BOOKKEEPING = "refused_bookkeeping"

#: The ladder of increments a progress turn can make by itself, in order: the first that applies is the turn's increment. Rungs 1, 3 and 4 always exist,
#: so "waiting on a person" is never the whole turn.
DELIVERABLE, METRIC_READ, EVIDENCE, RECOMMENDATION, SIMULATION = "deliverable", "metric_read", "evidence", "recommendation", "simulation"
LADDER = (DELIVERABLE, METRIC_READ, EVIDENCE, RECOMMENDATION, SIMULATION)
METHOD_OF = {DELIVERABLE: "rubric", METRIC_READ: "read", EVIDENCE: "evidence", RECOMMENDATION: "quality_score", SIMULATION: "simulation"}
INLINE, BACKGROUND = "inline", "background"
#: Fields a write may set that are bookkeeping, never progress on their own: who owns it, when it is due, when to be reminded.
BOOKKEEPING_FIELDS = frozenset({"assignee", "assigned_to_user_id", "owner", "owner_user_ids", "due_date", "scheduled_date", "deadline", "period",
                                "reminder", "reminders", "reminder_at", "remind_at"})


def plain_text(outcome: Any) -> str:
    if isinstance(outcome, Mapping):
        return str(outcome.get("text") or outcome.get("output") or "")
    return str(outcome or "")


@dataclass
class Increment:
    """One AI increment of a progress turn: its ``kind`` (a rung of ``LADDER``), the ``measure_id`` it is measured by, the ``before`` reading taken
    before the work starts (None until measured), the ``requirements`` the result is scored against, its ``size`` (``inline`` or ``background``), where it
    ``lands_on`` and the work ``item`` it comes from."""
    kind: str
    measure_id: str
    before: Optional[float] = None
    requirements: List[str] = field(default_factory=list)
    size: str = INLINE
    lands_on: Mapping[str, Any] = field(default_factory=dict)
    item: Mapping[str, Any] = field(default_factory=dict)
    method: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def doable_by_ai(item: Mapping[str, Any], means: Sequence[Mapping[str, Any]], available: Sequence[str] = ()) -> bool:
    """True when a work item is the AI's to do, decided on structured fields only: its ``actor`` is ``ai``; every input it lists exists (a record id in
    ``available`` or a means by name); no tool it needs is outward (a means whose ``outward`` flag is set: publish, send, pay); and the two independent
    checks of it (``checks``, two booleans from two separate judgments) agree. Anything else goes to the human ask."""
    names = {str(m.get("name")) for m in means}
    outward = {str(m.get("name")) for m in means if m.get("outward")}
    known = names | {str(a) for a in available}
    checks = [c for c in item.get("checks") or [] if isinstance(c, bool)]
    return (str(item.get("actor") or "") == "ai" and all(str(i) in known for i in item.get("inputs") or [])
            and not any(str(t) in outward for t in item.get("tools") or []) and len(checks) >= 2 and all(checks))


def choose_increment(milestone: Mapping[str, Any], metric_actions: Sequence[Mapping[str, Any]], work_items: Sequence[Mapping[str, Any]],
                     means: Sequence[Mapping[str, Any]] = ()) -> Optional[Increment]:
    """The turn's increment, the first rung of ``LADDER`` that applies, decided on structured fields: (1) an AI-doable work item of kind ``deliverable``,
    measured by the milestone's intermediate metric when upkeep defined one; (2) a metric upkeep read; (3) an AI-doable ``evidence`` item; (4) an
    AI-doable ``recommendation`` item; (5) a ``simulation`` item, only where a means to simulate is given. None only when no rung applies, which the caller
    reports as a gap in the work items, never as waiting on a person."""
    available = list(milestone.get("records") or [])
    lands_on = dict(milestone.get("lands_on") or {})
    child = next((a.get("child_metric") for a in metric_actions if isinstance(a.get("child_metric"), Mapping) and a["child_metric"].get("id")), None)
    doable = [w for w in work_items if doable_by_ai(w, means, available)]

    def from_item(kind: str, measure: str) -> Optional[Increment]:
        item = next((w for w in doable if str(w.get("kind") or "") == kind), None)
        if item is None:
            return None
        return Increment(kind, measure, None, [str(r) for r in item.get("requirements") or []], str(item.get("size") or INLINE), lands_on, dict(item), METHOD_OF[kind])

    solution = str(milestone.get("solution_id") or milestone.get("id") or "milestone")
    found = from_item(DELIVERABLE, str(child["id"]) if child else f"{solution}:deliverable")
    if found:
        return found
    read = next((a for a in metric_actions if a.get("action") == "read" and a.get("reading")), None)
    if read is not None:
        return Increment(METRIC_READ, str(read["metric_id"]), None, [], INLINE, lands_on, {"metric_id": read["metric_id"], "reading": read["reading"]}, "read")
    for kind in (EVIDENCE, RECOMMENDATION):
        found = from_item(kind, f"{solution}:{kind}")
        if found:
            return found
    if any(m.get("simulates") for m in means):
        return from_item(SIMULATION, f"{solution}:simulation")
    return None


def bookkeeping_only(outcome: Any) -> bool:
    """True when an outcome made no AI increment: it carries no ``increments`` with a ``measure_id`` and a measured ``before``, whatever writes it made (an
    owner, a due date or a reminder alone, or a question to a person alone, is not progress). Structured fields only."""
    if not isinstance(outcome, Mapping):
        return True
    increments = [i for i in outcome.get("increments") or [] if isinstance(i, Mapping) and i.get("measure_id") and i.get("before") is not None]
    return not increments


def only_bookkeeping_writes(writes: Sequence[Mapping[str, Any]]) -> bool:
    """True when every write sets bookkeeping fields only (``BOOKKEEPING_FIELDS``); an empty list is not bookkeeping."""
    fields = [set(map(str, w.get("fields") or [])) for w in writes]
    return bool(fields) and all(f and f <= BOOKKEEPING_FIELDS for f in fields)


class Verdicts:
    """The check of a draft: the check it is given, else the Goal Completion seat."""

    def __init__(self, seat: Any, goal: str, done_standard: str, check: Optional[Callable[[Any], Mapping[str, Any]]]):
        self.seat, self.goal, self.done_standard, self.check = seat, goal, done_standard, check

    def of(self, outcome: Any) -> Mapping[str, Any]:
        if self.check is not None:
            return self.check(outcome)
        found = take(self.seat, "goal-completion", goal=self.goal, done_standard=self.done_standard, outcome=outcome)
        return done(found) or {"met": False, "reason": "the goal could not be checked: " + (found.reason or "no checker")}


class BoundedReplan:
    """Replans with the untried reads before sending, within a budget; sends the current response and says the rest is still being worked on when the work is long; reports what was tried and what is missing when the condition cannot be met."""

    def __init__(self, goal: Any = None):
        self.goal = goal      # the Goal Completion seat, used when no check is given

    def result(self, outcome: Any, status: str, met: bool, replans: int, tried: List[str], missing: str, interim: str, **more: Any) -> Dict[str, Any]:
        return dict({"outcome": outcome, "status": status, "met": met, "replans": replans, "tried": tried, "missing": missing, "interim": interim,
                     "message": "" if met else more.pop("message", ""), "ignored_writes": []}, **more)

    def pursue(self, goal: str, done_standard: str, draft: Any, attempt: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
               means: Sequence[Mapping[str, Any]] = (), budget: Optional[Mapping[str, Any]] = None,
               announce: Optional[Callable[[str], Any]] = None, check: Optional[Callable[[Any], Mapping[str, Any]]] = None,
               progress: bool = False) -> Mapping[str, Any]:
        if progress and bookkeeping_only(draft):
            # A turn whose resolved intent is progress on a milestone or goal must carry an AI increment with a measured before; bookkeeping (an owner, a due
            # date, a reminder) or a question to a person alone is refused, whatever the check says. A bookkeeping request (progress false) is never refused here.
            return self.result(draft, REFUSED_BOOKKEEPING, False, 0, [], "no AI increment with a measured before", "",
                               message="A progress turn needs an AI increment (a deliverable, a reading or evidence) measured before and after; bookkeeping alone is not progress.")
        limits = dict(DEFAULT_BUDGET, **dict(budget or {}))
        started = time.monotonic()
        elapsed = limits.get("elapsed") or (lambda: time.monotonic() - started)
        verdicts = Verdicts(self.goal, goal, done_standard, check)
        verdict = verdicts.of(draft)
        if verdict.get("met"):
            return self.result(draft, MET, True, 0, [], "", "")
        if verdict.get("awaiting_person") is True:
            return self.result(draft, AWAITING_PERSON, True, 0, [], "", "")
        best, tried, interim, replans, ignored = draft, [], "", 0, []
        reads = [m for m in means if str(m.get("kind", "read")) == "read"]
        while attempt is not None and replans < int(limits["max_replans"]):
            untried = [m for m in reads if str(m.get("name")) not in tried]
            if not untried:
                break
            names = [str(m.get("name")) for m in untried]
            estimate = sum(float(m.get("cost_seconds") or 0.0) for m in untried)
            missing = str(verdict.get("reason") or "")
            if estimate > float(limits["wall_seconds"]) - float(elapsed()):
                break
            if estimate > float(limits["inline_seconds"]):
                if limits.get("background"):
                    return self.result(best, CONTINUING, False, replans, tried, missing, interim, **{"continue": {"means": names, "missing": missing}})
            replans += 1
            step = attempt({"means": names, "missing": missing, "replan": replans, "read_only": True})
            if step.get("writes"):
                ignored.append(list(step["writes"]))      # a replan never writes: what it reports is not trusted
                break
            tried.extend(str(n) for n in (step.get("means_used") or names))
            if plain_text(step.get("outcome")).strip():
                best = step["outcome"]
            verdict = verdicts.of(best)
            if verdict.get("met"):
                return self.result(best, MET_AFTER_REPLAN, True, replans, tried, "", interim)
        missing = str(verdict.get("reason") or "")
        out = self.result(best, UNMET_REPORTED, False, replans, tried, missing, interim)
        out["ignored_writes"] = ignored
        return out
