"""ConsciousnessComposition."""
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, TextIO
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import EsoiApplying
from hubofhubs.the_consciousness.feedback_learning.interface import FeedbackLearning
from hubofhubs.the_consciousness.judgment_calls.interface import JudgmentCalling
from hubofhubs.the_consciousness.prioritization.interface import Prioritizing
from hubofhubs.the_consciousness.representatives.interface import Representing
from hubofhubs.the_consciousness.request_intake.interface import RequestIntaking
from hubofhubs.the_consciousness.ai_session_experience.interface import SessionExperiencing
from hubofhubs.the_self.steps import DONE, listing, skipped, take
from hubofhubs.the_self.steps import done


@implementation("the-consciousness", "composition")
class ConsciousnessComposition:
    """Adapts the system to a person: the Representative carries the person's authority and preferences, Request Intake takes in what people ask,
    Prioritization turns what the person implies into priorities, Judgment Calls decides when to ask, and Feedback Learning proposes edits that
    ESOI Application applies to specs and metrics, never to prompts, with no approval step unless Judgment Calls decides to ask."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, representatives: Lazy[Representing], priorities: Lazy[Prioritizing], judgment: Lazy[JudgmentCalling],
                 feedback: Lazy[FeedbackLearning], esoi: Lazy[EsoiApplying], intake: Lazy[RequestIntaking], session: Lazy[SessionExperiencing] = None):
        self.representatives, self.priorities, self.judgment, self.feedback, self.esoi = representatives, priorities, judgment, feedback, esoi
        self.intake, self.session = intake, session

    def represent(self, person: str = "") -> Mapping[str, Any]:
        who = take(self.representatives, "the-representatives", person=person)
        weighed = take(self.priorities, "prioritization", person=person)
        return {"person": person, "representative": done(who) or {"person": person}, "priorities": done(weighed), "steps": listing([who, weighed])}

    def receive(self, person: str = "") -> Sequence[Mapping[str, Any]]:
        return list(done(take(self.intake, "request-intake", person=person)) or [])

    def converse(self, front_door: Callable[[str], Any], lines: Iterable[str], out: TextIO, person: str = "") -> Mapping[str, Any]:
        """The interactive entry: AI Session Experience (its terminal) reads what the person types, sends each line through ``front_door`` and draws the work and any question."""
        held = take(self.session, "ai-session-experience", method="converse", front_door=front_door, lines=lines, out=out, viewer_id=person)
        return {"exit_code": done(held), "steps": listing([held])}

    def decide(self, signal: Mapping[str, Any], person: str = "") -> Mapping[str, Any]:
        found = take(self.judgment, "judgment-calls", signal=signal, person=person)
        return {"decision": done(found), "steps": listing([found])}

    def order_asks(self, asks: Sequence[Mapping[str, Any]], person: str = "", stated: Optional[Mapping[str, Any]] = None, batch_limit: int = 0,
                   now: str = "") -> Mapping[str, Any]:
        """The asks to put in front of the person, in order. Judgment Calls decides for each ``ask`` (``id``, a risk ``severity`` and ``reason`` and the fields
        Prioritization reads) whether to ask at all; those it will ask go to Prioritization, which orders them by what they unblock, their deadline and what the
        person stated, and with a ``batch_limit`` puts only that many in front of the person and holds the rest with why. The others are listed with the decision."""
        decided = [(a, take(self.judgment, "judgment-calls", signal=a, person=person)) for a in asks]
        will_ask = [dict(a, kind=str(a.get("kind") or "ask")) for a, d in decided if (done(d) or {}).get("decision") == "ask"]
        others = [{"id": str(a.get("id")), "decision": (done(d) or {}).get("decision"), "reason": d.reason} for a, d in decided if (done(d) or {}).get("decision") != "ask"]
        ordered = (take(self.priorities, "prioritization", person=person, candidates=will_ask, subject="asks", stated=stated, batch_limit=batch_limit, now=now)
                   if will_ask else skipped("prioritization", "Judgment Calls decided to ask about nothing"))
        answer = done(ordered) or {}
        return {"asks": list(answer.get("ordered") or []), "held": list(answer.get("held") or []), "not_asked": others,
                "steps": listing([step for _, step in decided] + [ordered])}

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        if not feedback:
            return {"proposed": None, "steps": listing([skipped("feedback-learning", "no feedback was given")])}
        proposed = take(self.feedback, "feedback-learning", person=person, feedback=feedback)
        if proposed.status != DONE:
            return {"proposed": None, "steps": listing([proposed, skipped("esoi-application", "no proposed edit to apply")])}
        asked = take(self.judgment, "judgment-calls", signal={"severity": "none", "reason": "a change to specs or metrics from feedback"}, person=person)
        if asked.status != DONE:      # no decision is not a yes: nothing is applied that nobody decided on
            return {"proposed": done(proposed), "steps": listing([proposed, asked, skipped("esoi-application", "Judgment Calls could not decide")])}
        if (done(asked) or {}).get("decision") != "proceed":      # whether to ask is Judgment Calls' decision; by default no approval step
            return {"proposed": done(proposed), "decision": done(asked), "steps": listing([proposed, asked, skipped("esoi-application", "Judgment Calls asked first")])}
        applied = take(self.esoi, "esoi-application", change=done(proposed))
        return {"proposed": done(proposed), "steps": listing([proposed, asked, applied])}
