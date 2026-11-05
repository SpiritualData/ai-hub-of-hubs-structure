"""HigherMindComposition."""
from typing import Any, Mapping
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_intelligence.higher_mind.long_term_memory.interface import LongTermMemory
from hubofhubs.the_intelligence.higher_mind.objectives.interface import Objectives
from hubofhubs.the_intelligence.higher_mind.guidance.interface import Guiding
from hubofhubs.the_self.steps import listing, take
from hubofhubs.the_self.steps import done


@implementation("higher-mind", "composition")
class HigherMindComposition:
    """The long view for one request: the objectives it serves, what is remembered, and the nudge for the Planner."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, memory: Lazy[LongTermMemory], objectives: Lazy[Objectives], guidance: Lazy[Guiding]):
        self.memory, self.objectives, self.guidance = memory, objectives, guidance

    def view(self, request: str, person: str = "") -> Mapping[str, Any]:
        goals = take(self.objectives, "live-objectives", person=person)
        remembered = take(self.memory, "long-term-memory", query=request, person=person)
        nudge = take(self.guidance, "guidance", request=request, objectives=done(goals) or ())
        return {"objectives": done(goals) or [], "memory": done(remembered) or [], "guidance": done(nudge), "steps": listing([goals, remembered, nudge])}
