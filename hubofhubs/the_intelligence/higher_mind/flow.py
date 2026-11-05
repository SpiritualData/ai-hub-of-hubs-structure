"""HigherMindComposition."""
from typing import Any, Dict, List, Mapping, Optional, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_intelligence.higher_mind.long_term_memory.interface import LongTermMemory
from hubofhubs.the_intelligence.higher_mind.objectives.interface import Objectives
from hubofhubs.the_intelligence.higher_mind.guidance.interface import Guiding
from hubofhubs.the_consciousness.prioritization.interface import Prioritizing
from hubofhubs.the_self.steps import listing, skipped, take
from hubofhubs.the_self.steps import done


@implementation("higher-mind", "composition")
class HigherMindComposition:
    """The long view for one request: the objectives it serves, which of their solution milestones matter most to the person (Prioritization orders the milestones,
    never this flow), what is remembered, and the nudge for the Planner."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, memory: Lazy[LongTermMemory], objectives: Lazy[Objectives], guidance: Lazy[Guiding], priorities: Lazy[Prioritizing]):
        self.memory, self.objectives, self.guidance, self.priorities = memory, objectives, guidance, priorities

    def view(self, request: str, person: str = "", objectives: Sequence[Mapping[str, Any]] = (), stated: Optional[Mapping[str, Any]] = None,
             now: str = "") -> Mapping[str, Any]:
        goals = take(self.objectives, "live-objectives", person=person, objectives=objectives)
        rows = {str(r["id"]): r for r in done(goals) or ()}
        milestones: List[Dict[str, Any]] = [dict(o, kind="milestone", met=(rows[str(o.get("id"))]["state"] == "met") if str(o.get("id")) in rows else bool(o.get("met")))
                                           for o in objectives]
        ordered = (take(self.priorities, "prioritization", person=person, candidates=milestones, subject="goals", stated=stated, now=now) if milestones
                   else skipped("prioritization", "the person has no recorded objectives to order"))
        remembered = take(self.memory, "long-term-memory", query=request, person=person)
        nudge = take(self.guidance, "guidance", request=request, objectives=done(goals) or ())
        return {"objectives": done(goals) or [], "priority": done(ordered), "memory": done(remembered) or [], "guidance": done(nudge),
                "steps": listing([goals, ordered, remembered, nudge])}
