"""The flow of each part that composes others, written before the parts it calls.

Each class is the composition arm of one solution: it takes the solutions it uses as typed needs and calls each through the entry point the
solution declares (``hubofhubs.steps.take``), in the order the intent's solution coherence paragraph says. A solution that has no arm yet
comes back as a ``pending`` step, never as made-up output; the interface of every solution is declared in ``hubofhubs.seats`` first.

Top to bottom: ``IntelligenceComposition`` reads the long view, translates the request into a target with a budget, has the Subconscious
prepare, runs the Mind and checks the result; when the goal is unmet it returns to the Planner within the budget, and when the budget or the
authority runs out it goes to Judgment Calls. ``MindComposition`` runs Context Intake, the Planner, Delegation and the Response Writer, with the
Nervous System signal and Judgment Calls before a risky piece; ``CriticalThinkingComposition`` translates a request into a target and judges the
response against the resolved quality profile; ``ConsciousnessComposition`` represents the person, takes requests in and learns. The Self's own
flow, ``respond``, is in ``hubofhubs.whole``. Standard library plus the hub and ``esoi``."""
import functools
import inspect
import json
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy
from esoi.entry import call_entry, declared

from . import steps
from .card import Card
from .quality import resolve_profile
from .resolution import HUB
from .seats import (AgentSessions, CardsFromFiles, CardStore, ConnectedOperating, ContextTaking, CriticalThinking, Delegating, EsoiApplying,
                    FeedbackLearning, FileEditing, FileReading, FormAndContext, GoalCompleting, HigherMind, HumanAdapting, InformationProcessing,
                    InternalContexting, IntakeSourcing, Intuiting, JudgmentCalling, LongTermMemory, MetricTranslating, Objectives, Guiding,
                    Planning, Prioritizing, Proactive, Reasoning, Remembering, Representing, RequestIntaking, ResponseJudging, ResponseWriting,
                    RiskWatching, SearchBackend, Connecting)
from .signals import RiskSignal
from .steps import DONE, Step, listing, skipped, take



def done(found: Step) -> Any:
    """What a step returned, or None when it did not run."""
    return found.output if found.status == DONE else None


@implementation("the-body", "composition")
class BodyComposition:
    """Describes the form of the system: where its data lives (Internal Context), where its requests come from (Intake Sources) and which
    enduring integrations the AI may use (Hands), and keeps the run record the flow writes. Every part is specified to be adapted to a particular
    system; Body also owns the configuration, environment variables, secrets and stored authentication the tools need."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, internal: Lazy[InternalContexting], intake: Lazy[IntakeSourcing], hands: Lazy[Connecting]):
        self.internal, self.intake, self.hands = internal, intake, hands

    def describe(self, person: str = "") -> Mapping[str, Any]:
        found = [take(self.internal, "internal-context", method="declared"), take(self.intake, "intake-sources", method="sources"),
                 take(self.hands, "the-hands", system=person)]
        return {"sources": done(found[0]) or [], "intake": done(found[1]) or [], "integrations": done(found[2]) or [], "steps": listing(found)}

    def record_run(self, run: Mapping[str, Any]) -> str:
        return str(done(take(self.internal, "internal-context", method="record", run=run)) or "")


@implementation("internal-context", "composition")
class InternalContextComposition:
    """The system's own context as cards: read from the Card Store, and built from files by Cards From Files. The default declaration is local
    files at a standard location that belongs to the system, plus the configuration the tools need; a system replaces it by declaring its own
    sources, whose data belongs to the system or to a person, and the tool that reads them. The run record is kept as a card of the store."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, store: CardStore, builder: Lazy[CardsFromFiles]):
        self.store, self.builder = store, builder

    def declared(self) -> Sequence[Mapping[str, Any]]:
        return [{"kind": "local files", "where": "the standard folder of the system", "tool": "file-editing", "belongs_to": "system", "default": True},
                {"kind": "tool configuration", "where": "the environment of the process and the secrets it names", "tool": "", "belongs_to": "system", "default": True}]

    def read(self, query: str, limit: int = 5) -> Sequence[Card]:
        return list(self.store.search(query, limit=limit))

    def record(self, run: Mapping[str, Any]) -> str:
        identifier = f"run-{run.get('id') or int(time.time() * 1000)}"
        self.store.add(Card(identifier, json.dumps(run, default=str, sort_keys=True), source="run record", tags=("run-record",)))
        return identifier


@implementation("the-tools", "composition")
class ToolsComposition:
    """Uses the tool of a category through the category's own entry point, refusing a category the Representative's authority does not allow. Web
    Search is needed to build it; the other categories are built on first use, so a request that needs no file, operation or agent never asks for one."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, search: SearchBackend, reader: Lazy[FileReading], files: Lazy[FileEditing], operations: Lazy[ConnectedOperating],
                 sessions: Lazy[AgentSessions]):
        self.parts = {"web-search": search, "read-files": reader, "file-editing": files, "connected-system-operations": operations,
                      "delegated-agent-sessions": sessions}

    def use(self, category: str, request: Any, cancel_check: Optional[Callable[[], bool]] = None) -> Any:
        if category not in self.parts:
            raise ValueError(f"no tool category {category!r}; the categories are {', '.join(self.parts)}")
        found = declared(HUB, category)
        call = getattr(self.parts[category], found.entry)
        if cancel_check is not None and "cancel_check" in inspect.signature(call).parameters:      # a worker that can be stopped is given the hook
            call = functools.partial(call, cancel_check=cancel_check)
        return call_entry(call, request)


@implementation("higher-mind", "composition")
class HigherMindComposition:
    """The long view for one request: the objectives it serves, what is remembered, and the nudge for the Planner."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, memory: Lazy[LongTermMemory], objectives: Lazy[Objectives], guidance: Lazy[Guiding]):
        self.memory, self.objectives, self.guidance = memory, objectives, guidance

    def view(self, request: str, person: str = "") -> Mapping[str, Any]:
        goals = take(self.objectives, "live-objectives", person=person)
        remembered = take(self.memory, "long-term-memory", query=request, person=person)
        nudge = take(self.guidance, "planner-guidance", request=request, objectives=done(goals) or ())
        return {"objectives": done(goals) or [], "memory": done(remembered) or [], "guidance": done(nudge), "steps": listing([goals, remembered, nudge])}


@implementation("critical-thinking", "composition")
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
                 priorities: Optional[Mapping[str, Any]] = None, outcome: Optional[Any] = None) -> Mapping[str, Any]:
        profile = resolve_profile(representative, guidance, priorities)
        met = take(self.goal, "goal-completion", goal=request, done_standard=str((target or {}).get("done_standard", "")),
                   outcome=outcome if outcome is not None else response)
        judged = take(self.quality, "response-quality", response=response, evidence=evidence, profile=profile) if response else skipped(
            "response-quality", "no response to judge")
        return {"profile": profile.name, "goal": done(met), "findings": list(done(judged) or []), "steps": listing([met, judged])}


ACTION_OF_TOOL = {"web-search": "search", "the-science": "search", "read-files": "read", "file-editing": "update",
                  "connected-system-operations": "execute", "delegated-agent-sessions": "execute", "": "answer"}


def failed_pieces(results: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """The results of pieces that did not deliver: refused, failed, or a worker that said it did not meet its sub-goal."""
    return [r for r in results if r.get("refused") or r.get("error") or r.get("met") is False]


@implementation("the-mind", "composition")
class MindComposition:
    """The Mind for one request, in order: Context Intake, the Planner, Delegation and the Response Writer. Before a piece of work is handed on,
    the Nervous System signals how risky it is and Judgment Calls decides for this person; a piece that is not allowed is not delegated, and
    one that is asked about waits for the answer while the others go on. On a replan, Context Intake takes in what the workers brought last time."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, intake: Lazy[ContextTaking], planner: Lazy[Planning], delegation: Lazy[Delegating], writer: Lazy[ResponseWriting],
                 watch: Lazy[RiskWatching], judgment: Lazy[JudgmentCalling]):
        self.intake, self.planner, self.delegation, self.writer = intake, planner, delegation, writer
        self.watch, self.judgment = watch, judgment

    def think(self, request: str, authority: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
              guidance: Optional[Mapping[str, Any]] = None, profile: Optional[Any] = None, prepared: Optional[Mapping[str, Any]] = None,
              unmet: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None, budget: Optional[Any] = None,
              cancelled: Optional[Callable[[], bool]] = None) -> Mapping[str, Any]:
        authority = authority or {}
        log: List[Step] = [take(self.intake, "context-intake", request=request, prepared=prepared, outside=outside)]
        planned = take(self.planner, "request-planner", request=request, context=done(log[0]), target=target, guidance=guidance, unmet=unmet)
        log.append(planned)
        allowed: List[Mapping[str, Any]] = []
        asked: List[Mapping[str, Any]] = []
        for piece in done(planned) or ():
            digest = take(self.watch, "nervous-system", method="digest", user_message=request, step=1, max_steps=1,
                          plan_action=ACTION_OF_TOOL.get(str(piece.get("tool") or ""), "execute"), plan_goal=str(piece.get("piece", piece)))
            signal = take(self.watch, "nervous-system", digest=done(digest)) if digest.status == DONE else digest
            log.append(signal)
            if signal.status != DONE:      # a piece whose risk cannot be checked is not handed on
                asked.append({**piece, "refused": "risk could not be checked"})
                continue
            risk: RiskSignal = done(signal)
            decision = take(self.judgment, "judgment-calls", signal={"severity": risk.severity, "reason": risk.reason},
                            person=str(authority.get("person", "")))
            log.append(decision)
            if (done(decision) or {}).get("decision", "proceed") == "proceed":
                allowed.append(piece)
            else:
                asked.append({**piece, "refused": "asked", "decision": done(decision)})
        if not done(planned):
            log += [skipped("nervous-system", "no piece to check yet"), skipped("judgment-calls", "no piece to decide on yet")]
        handed = take(self.delegation, "work-delegation", pieces=allowed, authority=authority, budget=budget, cancelled=cancelled)
        results = list(done(handed) or []) + [{"piece": str(p.get("piece", "")), "tool": str(p.get("tool", "")), "refused": p["refused"], "items": [], "text": ""}
                                              for p in asked]
        written = take(self.writer, "response-writer", results=results, profile=profile)
        log += [handed, written]
        return {"text": done(written) or "", "results": results, "pieces": list(done(planned) or []), "steps": listing(log)}


def outside_of(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """What the workers brought, in the shape Context Intake takes for the outside: their text and their sources."""
    return {"answer": "\n".join(str(r.get("text", "")) for r in results if r.get("text")), "items": [i for r in results for i in r.get("items") or ()]}


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
        weighed = take(self.priorities, "human-prioritization", person=person)
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
