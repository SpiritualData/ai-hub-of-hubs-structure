"""IntelligenceComposition."""
from typing import Any, Callable, List, Mapping, Optional, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_consciousness.representatives.quality import resolve_profile
from hubofhubs.the_intelligence.critical_thinking.interface import CriticalThinking
from hubofhubs.the_intelligence.higher_mind.interface import HigherMind
from hubofhubs.the_consciousness.judgment_calls.interface import JudgmentCalling
from hubofhubs.the_consciousness.prioritization.interface import Prioritizing
from hubofhubs.the_intelligence.proactivity.interface import Proactive
from hubofhubs.the_intelligence.proactivity.triggers import attach_events, candidate_of, in_priority_order
from hubofhubs.the_intelligence.mind.interface import Reasoning
from hubofhubs.the_intelligence.subconscious.interface import Remembering
from hubofhubs.the_self.steps import Step, listing, skipped, take
from hubofhubs.the_self.steps import done
from hubofhubs.the_intelligence.mind.flow import failed_pieces, outside_of


def most_important(long_view: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """The objective the person cares about most, as Prioritization ordered them; with no order, the first of the hierarchy."""
    rows = long_view.get("objectives") or []
    first = ((long_view.get("priority") or {}).get("ordered") or [{}])[0].get("id")
    return next((r for r in rows if str(r.get("id")) == str(first)), rows[0] if rows else None)


@implementation("the-intelligence", "composition")
class IntelligenceComposition:
    """One request through Intelligence: Higher Mind gives the long view, Critical Thinking translates the request into a target with a budget,
    the Subconscious prepares information, the Mind plans, delegates and writes, and Critical Thinking checks the goal and the response quality.
    When Goal Completion says the goal is unmet the flow returns to the Planner with what failed, within the attempts the budget allows; when the
    budget or the authority runs out it goes to Judgment Calls. Proactivity says what is due without being asked, and Prioritization, which
    Consciousness gives the person's priorities, says what matters first among the due work and the other work that is waiting."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, higher: Lazy[HigherMind], subconscious: Lazy[Remembering], critical: Lazy[CriticalThinking], mind: Lazy[Reasoning],
                 judgment: Lazy[JudgmentCalling], proactivity: Lazy[Proactive], priorities: Lazy[Prioritizing]):
        self.higher, self.subconscious, self.critical, self.mind = higher, subconscious, critical, mind
        self.judgment, self.proactivity, self.priorities = judgment, proactivity, priorities

    def proactive(self, schedules: Sequence[Mapping[str, Any]], now: str = "", person: str = "", candidates: Sequence[Mapping[str, Any]] = (),
                  stated: Optional[Mapping[str, Any]] = None, events: Sequence[Mapping[str, Any]] = ()) -> Sequence[Mapping[str, Any]]:
        """What to do unasked, most important first: Proactivity says which standing work is due (the events a consumer pulled through Body's Intake Sources
        count as events of the schedules that name their source), Prioritization puts the due work and ``candidates`` (the other work waiting, such as open
        asks) in order for this person, and the triggers come back in that order with each one's rank and reason. Without Prioritization the due order stays."""
        due = take(self.proactivity, "proactivity", schedules=attach_events(schedules, events), now=now)
        triggers = list(done(due) or [])
        ordered = take(self.priorities, "prioritization", person=person, candidates=[candidate_of(t, schedules) for t in triggers] + list(candidates),
                       stated=stated, now=now)
        return in_priority_order(triggers, candidates, done(ordered))

    def process(self, request: str, person: str = "", representative: Optional[Mapping[str, Any]] = None,
                priorities: Optional[Mapping[str, Any]] = None, cancelled: Optional[Callable[[], bool]] = None,
                objectives: Sequence[Mapping[str, Any]] = (), stated: Optional[Mapping[str, Any]] = None, now: str = "",
                records: Any = None, own_passes: Optional[Mapping[str, Callable[..., Mapping[str, Any]]]] = None, knowledge: str = "retrieved",
                ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        view = take(self.higher, "higher-mind", request=request, person=person, objectives=objectives, stated=stated, now=now)
        long_view = done(view) or {}
        prepared = take(self.subconscious, "the-subconscious", method="prepare", request=request,
                        **({"records": records, "knowledge": knowledge} if records is not None else {}))
        briefs = (done(prepared) or {}).get("solutions") or {}
        considered_step = (take(self.critical, "critical-thinking", method="consider", request=request, briefs=briefs, own_passes=own_passes, ask=ask)
                           if briefs.get("solutions") else skipped("critical-thinking", "the request concerns no solution of the consumer's records"
                                                                   if records is not None else "no ESOI records were given"))
        considered = {**dict(done(considered_step) or {}), "prompts": {b["solution_id"]: b.get("prompt", "") for b in briefs.get("solutions") or []}}
        own_targets = [{**dict(f.get("target") or {}), "solution_id": f["solution_id"], "name": f.get("name", "")}
                       for f in considered.get("findings") or [] if f.get("applies") is not False]
        translated = take(self.critical, "critical-thinking", method="translate", request=request, parent=most_important(long_view),
                          **({"solutions": own_targets} if own_targets else {}))
        target = (done(translated) or {}).get("target")
        profile_inputs = {"representative": representative, "guidance": long_view.get("guidance"), "priorities": priorities}
        budget = dict((target or {}).get("budget") or {})
        attempts = int(budget.get("attempts") or 1)
        log: List[Step] = [view, prepared, considered_step, translated]
        with_solutions = {"considered": considered} if considered.get("findings") else {}
        pieces_checked: Step = skipped("critical-thinking", "no piece is tied to a solution")
        unmet: Optional[Mapping[str, Any]] = None
        outside: Optional[Mapping[str, Any]] = None
        checked: Step = skipped("critical-thinking", "the mind produced nothing to check")
        text, results, escalation, stopped = "", [], None, ""
        for attempt in range(1, max(attempts, 1) + 1):
            thought = take(self.mind, "the-mind", request=request, authority=representative, target=target, guidance=long_view.get("guidance"),
                           profile=resolve_profile(**profile_inputs), prepared=done(prepared), unmet=unmet, outside=outside, budget=budget,
                           cancelled=cancelled, **with_solutions)
            thinking = done(thought) or {}
            text, results = thinking.get("text", ""), thinking.get("results", [])
            evidence = " ".join(str(i.get("url", "")) + " " + str(i.get("snippet", "")) for r in results for i in r.get("items") or ())
            checked = take(self.critical, "critical-thinking", method="evaluate", request=request, response=text, target=target, evidence=evidence,
                           outcome={"text": text, "refused": next((r["refused"] for r in results if r.get("refused")), ""),
                                    "error": next((r["error"] for r in results if r.get("error")), "")}, **profile_inputs)
            log += [thought, checked]
            goal = (done(checked) or {}).get("goal")
            short: List[Mapping[str, Any]] = []
            if with_solutions:      # each piece against its own solution's target: a piece short of it returns to the Planner like an unmet goal
                pieces_checked = take(self.critical, "critical-thinking", method="check_pieces", results=results, considered=considered)
                log.append(pieces_checked)
                verdict = done(pieces_checked) or {}
                short = [p for p in verdict.get("pieces") or [] if p.get("met") is False]
                if short or (verdict.get("combined") or {}).get("met") is False:
                    goal = {"met": False, "reason": "; ".join([f"{p['solution_id']}: {p.get('reason') or 'short of its target'}" for p in short]
                                                              + list((verdict.get("combined") or {}).get("reasons") or []))}
            if goal is None or goal.get("met"):      # met, or no check to replan on
                break
            if any(r.get("refused") in ("authority", "cancelled") for r in results):
                stopped = next(r["refused"] for r in results if r.get("refused") in ("authority", "cancelled"))
                break
            if attempt >= attempts:
                stopped = "budget"
                break
            unmet = {"failed_pieces": [str(r.get("piece", "")) for r in failed_pieces(results)] + [str(p.get("piece", "")) for p in short],
                     "reason": goal.get("reason", "")}
            outside = outside_of(results)
        if with_solutions:      # what the passes and the last checks taught, written back for the next request's prompts
            log.append(take(self.critical, "critical-thinking", method="write_back", considered=considered, checked=done(pieces_checked) or {}, today=now[:10]))
        if stopped and stopped != "cancelled":
            asked = take(self.judgment, "judgment-calls", signal={"severity": "none", "reason": (done(checked) or {}).get("goal", {}).get("reason", "")},
                         person=str((representative or {}).get("person", "")), context={"stopped": stopped})
            log.append(asked)
            escalation = done(asked)
        return {"answer": text, "results": results, "attempts": attempt, "stopped": stopped, "escalation": escalation, "steps": listing(log),
                **({"considered": considered} if with_solutions else {})}
