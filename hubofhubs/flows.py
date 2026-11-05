"""The flow of each part that composes others, written before the parts it calls.

Each class is the composition arm of one solution: it takes the solutions it uses as typed needs and calls each through the entry point the
solution declares (``hubofhubs.steps.take``), in the order the intent's solution coherence paragraph says. A solution that has no arm yet
comes back as a ``pending`` step, never as made-up output; the interface of every solution is declared in ``hubofhubs.seats`` first.

Top to bottom: ``IntelligenceComposition`` reads the long view, translates the request into a target, has the Subconscious prepare, runs the
Mind and checks the result; ``MindComposition`` runs Context Intake, the Planner, Delegation and the Response Writer, with the Nervous System
signal and Judgment Calls before a risky piece; ``CriticalThinkingComposition`` translates a request into a target and judges the response
against the resolved quality profile. The Self's own flow, ``respond``, is in ``hubofhubs.whole``. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy
from esoi.entry import call_entry, declared

from . import steps
from .card import Card
from .quality import resolve_profile
from .resolution import HUB
from .seats import (CardsFromFiles, CardStore, Connecting, ConnectedOperating, Delegating, EsoiApplying, FeedbackLearning, FileEditing,
                    AgentSessions, GoalCompleting, Guiding, HigherMind, HumanAdapting, InformationProcessing, Intuiting, JudgmentCalling,
                    LongTermMemory, MetricTranslating, ContextTaking, Objectives, PersonalDataLocating, Planning, Prioritizing, Reasoning,
                    Remembering, Representing, ResponseJudging, ResponseWriting, RiskWatching, SearchBackend, CriticalThinking,
                    InternalContexting, FormAndContext)
from .steps import DONE, Step, listing, skipped, take


def done(found: Step) -> Any:
    """What a step returned, or None when it did not run."""
    return found.output if found.status == DONE else None


@implementation("the-body", "composition")
class BodyComposition:
    """Describes the form of the system: where its data lives (Internal Context) and which enduring integrations the AI may use (Hands). Every
    part is specified to be adapted to a particular system."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, internal: Lazy[InternalContexting], hands: Lazy[Connecting]):
        self.internal, self.hands = internal, hands

    def describe(self, person: str = "") -> Mapping[str, Any]:
        found = [take(self.internal, "internal-context", method="declared"), take(self.hands, "connect-any-integration", system=person)]
        return {"sources": done(found[0]) or [], "integrations": done(found[1]) or [], "steps": listing(found)}


@implementation("internal-context", "composition")
class InternalContextComposition:
    """The system's own context as cards: read from the Card Store, and built from files by Cards From Files. The default declaration is local
    files at a standard location, which a system replaces by declaring its own sources and the tool that reads them."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, store: CardStore, builder: Lazy[CardsFromFiles]):
        self.store, self.builder = store, builder

    def declared(self) -> Sequence[Mapping[str, Any]]:
        return [{"kind": "local files", "where": "the standard folder of the system", "tool": "edit-files", "default": True}]

    def read(self, query: str, limit: int = 5) -> Sequence[Card]:
        return list(self.store.search(query, limit=limit))


@implementation("use-tools", "composition")
class ToolsComposition:
    """Uses the tool of a category through the category's own entry point. Web Search is needed to build it; the other categories are built
    on first use, so a request that needs no file, operation or agent never asks for one."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, search: SearchBackend, files: Lazy[FileEditing], operations: Lazy[ConnectedOperating], sessions: Lazy[AgentSessions],
                 locations: Lazy[PersonalDataLocating]):
        self.parts = {"search-backend": search, "edit-files": files, "connected-system-operations": operations,
                      "delegated-agent-sessions": sessions, "personal-data-locations": locations}

    def use(self, category: str, request: Any) -> Any:
        if category not in self.parts:
            raise ValueError(f"no tool category {category!r}; the categories are {', '.join(self.parts)}")
        found = declared(HUB, category)
        return call_entry(getattr(self.parts[category], found.entry), request)


@implementation("higher-mind", "composition")
class HigherMindComposition:
    """The long view for one request: the objectives it serves, what is remembered, and the nudge for the Planner."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, memory: Lazy[LongTermMemory], objectives: Lazy[Objectives], guidance: Lazy[Guiding]):
        self.memory, self.objectives, self.guidance = memory, objectives, guidance

    def view(self, request: str, person: str = "") -> Mapping[str, Any]:
        goals = take(self.objectives, "hold-objectives", person=person)
        remembered = take(self.memory, "long-term-memory", query=request, person=person)
        nudge = take(self.guidance, "guidance", request=request, objectives=done(goals) or ())
        return {"objectives": done(goals) or [], "memory": done(remembered) or [], "guidance": done(nudge), "steps": listing([goals, remembered, nudge])}


@implementation("think-critically", "composition")
class CriticalThinkingComposition:
    """A request becomes a target (Metric Translation, recorded as a spec through ESOI Application), and the response is held to it: Goal
    Completion says whether the goal was met, and Response Quality judges the response against the quality profile resolved for this request
    (the Representative's, Guidance's and Prioritization's, else the default)."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, metric: Lazy[MetricTranslating], esoi: Lazy[EsoiApplying], goal: Lazy[GoalCompleting], quality: Lazy[ResponseJudging]):
        self.metric, self.esoi, self.goal, self.quality = metric, esoi, goal, quality

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        found = take(self.metric, "metric-translation", request=request, parent=parent)
        recorded = take(self.esoi, "esoi-application", change={"metric": done(found)}) if found.status == DONE else skipped(
            "esoi-application", "no target to record as a spec")
        return {"target": done(found), "steps": listing([found, recorded])}

    def evaluate(self, request: str, response: str = "", target: Optional[Mapping[str, Any]] = None, evidence: str = "",
                 representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                 priorities: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        profile = resolve_profile(representative, guidance, priorities)
        met = take(self.goal, "goal-completion", goal=request, done_standard=str((target or {}).get("done_standard", "")), outcome=response)
        judged = take(self.quality, "response-quality", response=response, evidence=evidence, profile=profile) if response else skipped(
            "response-quality", "no response to judge")
        return {"profile": profile.name, "goal": done(met), "findings": list(done(judged) or []), "steps": listing([met, judged])}


@implementation("reason-and-answer", "composition")
class MindComposition:
    """The Mind for one request, in order: Context Intake, the Planner, Delegation and the Response Writer. Before a piece of work is handed on,
    the Nervous System signals and Judgment Calls decides for this person; a piece that is not allowed is not delegated. With no piece (the
    Planner has no arm yet) nothing is checked and Delegation and the Response Writer report their own state."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, intake: Lazy[ContextTaking], planner: Lazy[Planning], delegation: Lazy[Delegating], writer: Lazy[ResponseWriting],
                 watch: Lazy[RiskWatching], judgment: Lazy[JudgmentCalling]):
        self.intake, self.planner, self.delegation, self.writer = intake, planner, delegation, writer
        self.watch, self.judgment = watch, judgment

    def think(self, request: str, authority: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
              guidance: Optional[Mapping[str, Any]] = None, profile: Optional[Any] = None,
              prepared: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        authority = authority or {}
        log: List[Step] = [take(self.intake, "context-intake", request=request, prepared=prepared, outside=None)]
        planned = take(self.planner, "planner", request=request, context=done(log[0]), target=target, guidance=guidance)
        log.append(planned)
        allowed: List[Mapping[str, Any]] = []
        for piece in done(planned) or ():
            digest_text = str(piece.get("piece", piece))
            digest = take(self.watch, "watch-for-risk", method="digest", user_message=request, step=1, max_steps=1, plan_action=digest_text,
                          plan_goal=request)
            signal = take(self.watch, "watch-for-risk", digest=done(digest)) if digest.status == DONE else digest
            log.append(signal)
            if signal.status != DONE:      # a piece whose risk cannot be checked is not handed on
                continue
            decision = take(self.judgment, "judgment-calls", signal={"signal": getattr(done(signal), "signal", "proceed")},
                            person=str(authority.get("person", "")))
            log.append(decision)
            if (done(decision) or {}).get("decision", "proceed") == "proceed":
                allowed.append(piece)
        if not done(planned):
            log += [skipped("watch-for-risk", "no piece to check yet"), skipped("judgment-calls", "no piece to decide on yet")]
        handed = take(self.delegation, "delegation", pieces=allowed, authority=authority)
        written = take(self.writer, "response-writer", results=done(handed) or [], profile=profile)
        log += [handed, written]
        return {"text": done(written) or "", "steps": listing(log)}


@implementation("the-intelligence", "composition")
class IntelligenceComposition:
    """One request through Intelligence: Higher Mind gives the long view, Critical Thinking translates the request into a target, the Subconscious
    prepares information, the Mind plans and writes, and Critical Thinking checks the goal and the response quality. The Nervous System and
    Judgment Calls act inside the Mind, before a risky piece."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, higher: Lazy[HigherMind], subconscious: Lazy[Remembering], critical: Lazy[CriticalThinking], mind: Lazy[Reasoning]):
        self.higher, self.subconscious, self.critical, self.mind = higher, subconscious, critical, mind

    def process(self, request: str, person: str = "", representative: Optional[Mapping[str, Any]] = None,
                priorities: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        view = take(self.higher, "higher-mind", request=request, person=person)
        long_view = done(view) or {}
        translated = take(self.critical, "think-critically", method="translate", request=request, parent=(long_view.get("objectives") or [None])[0])
        target = (done(translated) or {}).get("target")
        prepared = take(self.subconscious, "remember-and-recall", method="prepare", request=request)
        profile_inputs = {"representative": representative, "guidance": long_view.get("guidance"), "priorities": priorities}
        thought = take(self.mind, "reason-and-answer", request=request, authority=representative, target=target, guidance=long_view.get("guidance"),
                       profile=resolve_profile(**profile_inputs), prepared=done(prepared))
        text = (done(thought) or {}).get("text", "")
        checked = take(self.critical, "think-critically", method="evaluate", request=request, response=text, target=target, **profile_inputs)
        return {"answer": text, "steps": listing([view, translated, prepared, thought, checked])}


@implementation("the-consciousness", "composition")
class ConsciousnessComposition:
    """Adapts the system to a person: the Representative carries the person's authority and preferences, Prioritization turns what the person
    implies into priorities, Judgment Calls decides when to ask, and Feedback Learning proposes edits that ESOI Application applies to specs
    and metrics, never to prompts."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, representatives: Lazy[Representing], priorities: Lazy[Prioritizing], judgment: Lazy[JudgmentCalling],
                 feedback: Lazy[FeedbackLearning], esoi: Lazy[EsoiApplying]):
        self.representatives, self.priorities, self.judgment, self.feedback, self.esoi = representatives, priorities, judgment, feedback, esoi

    def represent(self, person: str = "") -> Mapping[str, Any]:
        who = take(self.representatives, "ai-representatives", person=person)
        weighed = take(self.priorities, "prioritization", person=person)
        return {"person": person, "representative": done(who) or {"person": person}, "priorities": done(weighed), "steps": listing([who, weighed])}

    def decide(self, signal: Mapping[str, Any], person: str = "") -> Mapping[str, Any]:
        found = take(self.judgment, "judgment-calls", signal=signal, person=person)
        return {"decision": done(found), "steps": listing([found])}

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        if not feedback:
            return {"proposed": None, "steps": listing([skipped("feedback-learning", "no feedback was given")])}
        proposed = take(self.feedback, "feedback-learning", person=person, feedback=feedback)
        applied = take(self.esoi, "esoi-application", change=done(proposed)) if proposed.status == DONE else skipped(
            "esoi-application", "no proposed edit to apply")
        return {"proposed": done(proposed), "steps": listing([proposed, applied])}
