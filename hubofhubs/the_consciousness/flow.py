"""ConsciousnessComposition."""
from typing import Any, Mapping, Optional, Sequence
from esoi import implementation
from esoi.assemble import Lazy
from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import EsoiApplying
from hubofhubs.the_consciousness.feedback_learning.interface import FeedbackLearning
from hubofhubs.the_consciousness.judgment_calls.interface import JudgmentCalling
from hubofhubs.the_consciousness.prioritization.interface import Prioritizing
from hubofhubs.the_consciousness.representatives.interface import Representing
from hubofhubs.the_consciousness.request_intake.interface import RequestIntaking
from hubofhubs.the_self.steps import DONE, listing, skipped, take
from hubofhubs.the_self.steps import done


@implementation("the-consciousness", "composition")
class ConsciousnessComposition:
    """Adapts the system to a person: the Representative carries the person's authority and preferences, Request Intake takes in what people ask,
    Prioritization turns what the person implies into priorities, Judgment Calls decides when to ask, and Feedback Learning proposes edits that
    ESOI Application applies to specs and metrics, never to prompts, with no approval step unless Judgment Calls decides to ask."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, representatives: Lazy[Representing], priorities: Lazy[Prioritizing], judgment: Lazy[JudgmentCalling],
                 feedback: Lazy[FeedbackLearning], esoi: Lazy[EsoiApplying], intake: Lazy[RequestIntaking]):
        self.representatives, self.priorities, self.judgment, self.feedback, self.esoi = representatives, priorities, judgment, feedback, esoi
        self.intake = intake

    def represent(self, person: str = "") -> Mapping[str, Any]:
        who = take(self.representatives, "the-representatives", person=person)
        weighed = take(self.priorities, "prioritization", person=person)
        return {"person": person, "representative": done(who) or {"person": person}, "priorities": done(weighed), "steps": listing([who, weighed])}

    def receive(self, person: str = "") -> Sequence[Mapping[str, Any]]:
        return list(done(take(self.intake, "request-intake", person=person)) or [])

    def decide(self, signal: Mapping[str, Any], person: str = "") -> Mapping[str, Any]:
        found = take(self.judgment, "judgment-calls", signal=signal, person=person)
        return {"decision": done(found), "steps": listing([found])}

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        if not feedback:
            return {"proposed": None, "steps": listing([skipped("feedback-learning", "no feedback was given")])}
        proposed = take(self.feedback, "feedback-learning", person=person, feedback=feedback)
        if proposed.status != DONE:
            return {"proposed": None, "steps": listing([proposed, skipped("esoi-application", "no proposed edit to apply")])}
        asked = take(self.judgment, "judgment-calls", signal={"severity": "none", "reason": "a change to specs or metrics from feedback"}, person=person)
        if (done(asked) or {}).get("decision", "proceed") != "proceed":      # whether to ask is Judgment Calls' decision; by default no approval step
            return {"proposed": done(proposed), "decision": done(asked), "steps": listing([proposed, asked, skipped("esoi-application", "Judgment Calls asked first")])}
        applied = take(self.esoi, "esoi-application", change=done(proposed))
        return {"proposed": done(proposed), "steps": listing([proposed, asked, applied])}
