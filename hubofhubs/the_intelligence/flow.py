"""IntelligenceComposition."""
from typing import Any, Callable, List, Mapping, Optional, Sequence
from esoi import implementation
from esoi.assemble import Lazy
from hubofhubs.the_consciousness.representatives.quality import resolve_profile
from hubofhubs.the_intelligence.critical_thinking.interface import CriticalThinking
from hubofhubs.the_intelligence.higher_mind.interface import HigherMind
from hubofhubs.the_consciousness.judgment_calls.interface import JudgmentCalling
from hubofhubs.the_intelligence.proactivity.interface import Proactive
from hubofhubs.the_intelligence.mind.interface import Reasoning
from hubofhubs.the_intelligence.subconscious.interface import Remembering
from hubofhubs.the_self.steps import Step, listing, skipped, take
from hubofhubs.the_self.steps import done
from hubofhubs.the_intelligence.mind.flow import failed_pieces, outside_of


@implementation("the-intelligence", "composition")
class IntelligenceComposition:
    """One request through Intelligence: Higher Mind gives the long view, Critical Thinking translates the request into a target with a budget,
    the Subconscious prepares information, the Mind plans, delegates and writes, and Critical Thinking checks the goal and the response quality.
    When Goal Completion says the goal is unmet the flow returns to the Planner with what failed, within the attempts the budget allows; when the
    budget or the authority runs out it goes to Judgment Calls. Proactivity says what is due without being asked."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, higher: Lazy[HigherMind], subconscious: Lazy[Remembering], critical: Lazy[CriticalThinking], mind: Lazy[Reasoning],
                 judgment: Lazy[JudgmentCalling], proactivity: Lazy[Proactive]):
        self.higher, self.subconscious, self.critical, self.mind = higher, subconscious, critical, mind
        self.judgment, self.proactivity = judgment, proactivity

    def proactive(self, schedules: Sequence[Mapping[str, Any]], now: str = "") -> Sequence[Mapping[str, Any]]:
        return list(done(take(self.proactivity, "proactivity", schedules=schedules, now=now)) or [])

    def process(self, request: str, person: str = "", representative: Optional[Mapping[str, Any]] = None,
                priorities: Optional[Mapping[str, Any]] = None, cancelled: Optional[Callable[[], bool]] = None) -> Mapping[str, Any]:
        view = take(self.higher, "higher-mind", request=request, person=person)
        long_view = done(view) or {}
        translated = take(self.critical, "critical-thinking", method="translate", request=request, parent=(long_view.get("objectives") or [None])[0])
        target = (done(translated) or {}).get("target")
        prepared = take(self.subconscious, "the-subconscious", method="prepare", request=request)
        profile_inputs = {"representative": representative, "guidance": long_view.get("guidance"), "priorities": priorities}
        budget = dict((target or {}).get("budget") or {})
        attempts = int(budget.get("attempts") or 1)
        log: List[Step] = [view, translated, prepared]
        unmet: Optional[Mapping[str, Any]] = None
        outside: Optional[Mapping[str, Any]] = None
        checked: Step = skipped("critical-thinking", "the mind produced nothing to check")
        text, results, escalation, stopped = "", [], None, ""
        for attempt in range(1, max(attempts, 1) + 1):
            thought = take(self.mind, "the-mind", request=request, authority=representative, target=target, guidance=long_view.get("guidance"),
                           profile=resolve_profile(**profile_inputs), prepared=done(prepared), unmet=unmet, outside=outside, budget=budget,
                           cancelled=cancelled)
            thinking = done(thought) or {}
            text, results = thinking.get("text", ""), thinking.get("results", [])
            evidence = " ".join(str(i.get("url", "")) + " " + str(i.get("snippet", "")) for r in results for i in r.get("items") or ())
            checked = take(self.critical, "critical-thinking", method="evaluate", request=request, response=text, target=target, evidence=evidence,
                           outcome={"text": text, "refused": next((r["refused"] for r in results if r.get("refused")), "")}, **profile_inputs)
            log += [thought, checked]
            goal = (done(checked) or {}).get("goal")
            if goal is None or goal.get("met"):      # met, or no check to replan on
                break
            if any(r.get("refused") in ("authority", "cancelled") for r in results):
                stopped = next(r["refused"] for r in results if r.get("refused") in ("authority", "cancelled"))
                break
            if attempt >= attempts:
                stopped = "budget"
                break
            unmet = {"failed_pieces": [str(r.get("piece", "")) for r in failed_pieces(results)], "reason": goal.get("reason", "")}
            outside = outside_of(results)
        if stopped and stopped != "cancelled":
            asked = take(self.judgment, "judgment-calls", signal={"severity": "none", "reason": (done(checked) or {}).get("goal", {}).get("reason", "")},
                         person=str((representative or {}).get("person", "")), context={"stopped": stopped})
            log.append(asked)
            escalation = done(asked)
        return {"answer": text, "results": results, "attempts": attempt, "stopped": stopped, "escalation": escalation, "steps": listing(log)}
