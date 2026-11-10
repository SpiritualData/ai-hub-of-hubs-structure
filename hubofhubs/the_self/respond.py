"""The Self's own flow, ``respond``: the whole answers a request by calling Consciousness, Body and Intelligence in order, records the run in Body's
run store and has Integrity audit it. Standard library plus the hub and ``esoi``."""
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_self.assembler.oneline import Result
from hubofhubs.the_body.interface import FormAndContext
from hubofhubs.the_self.integrity.interface import Genericity
from hubofhubs.the_consciousness.interface import HumanAdapting
from hubofhubs.the_intelligence.interface import InformationProcessing
from hubofhubs.the_world.interface import TakingIn
from hubofhubs.the_self.assembler.interface import WholeAssembling
from hubofhubs.the_self.role_understanding.interface import RoleUnderstanding
from hubofhubs.the_self.steps import DONE, UNAVAILABLE, Step, listing, support, take


def sources_of(results: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for result in results:
        for item in result.get("items") or ():
            seen.setdefault(str(item.get("url") or item.get("title")), dict(item))
    return list(seen.values())


def cannot_answer(reason: str) -> str:
    """What the person reads when the step the answer depends on could not run: the plain fact and what to do, never a class name."""
    detail = reason.split(": ", 1)[-1].strip() if reason else ""
    return ("I could not finish this" + (f": {detail}" if detail else "") + ". Run it again; if it keeps happening, `ahohs --help` lists what can be set up.")


def stop_line(thought: Mapping[str, Any], decision: Mapping[str, Any]) -> str:
    """Why the run stopped, in words that are true: the attempts spent without the goal met, and who is asked next."""
    reason = str(thought.get("reason") or "the answer did not meet its standard")
    asked = f"{decision.get('decision') or ''} {decision.get('to') or ''}".strip()
    if thought.get("stopped") == "authority":
        return "stopped: the request does not carry the authority this needs" + (f"; {asked}" if asked else "")
    return f"stopped after {thought.get('attempts', 1)} attempt(s) without meeting the goal ({reason})" + (f"; {asked}" if asked else "")


@implementation("the-self", "composition")
class SelfComposition:
    """The Self responds as the whole. Its flow, in order: Consciousness represents the person, Body describes where the system's data lives,
    Intelligence processes the request with the Representative's authority (World's tools do the outside work from there), Role Understanding states what
    Intelligence is for, Body keeps the run record and Integrity audits it, and Consciousness learns from feedback when there is some. The result lists the step of every part and says
    which have no arm yet. World is asked, in ``health``, how current the research is. ``serve`` takes the waiting requests in through Consciousness; ``act_unasked`` responds to what Proactivity says is due, in the order Prioritization gives.
    Every part, World included, is built on first use, so a seat that cannot be built is a pending step, not a failure of the rest, and a request that needs no key runs with none."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, world: Lazy[TakingIn], assembler: Lazy[WholeAssembling], integrity: Lazy[Genericity], body: Lazy[FormAndContext], intelligence: Lazy[InformationProcessing],
                 consciousness: Lazy[HumanAdapting], roles: Lazy[RoleUnderstanding]):
        self.world, self.assembler, self.integrity = world, assembler, integrity
        self.body, self.intelligence, self.consciousness, self.roles = body, intelligence, consciousness, roles

    def respond(self, request: str, person: str = "", feedback: Optional[Mapping[str, Any]] = None,
                cancelled: Optional[Callable[[], bool]] = None) -> Result:
        began = time.time()
        if not str(request or "").strip():      # nothing was asked: say so, and what to type
            return Result(input=str(request or ""), seat="the-self", answer="Nothing to answer yet: type a question or a task, for example \"What can you do?\".")
        known = support(self.consciousness, "the-consciousness", person=person)       # who it is for: it shapes the answer, the answer does not depend on it
        context = support(self.body, "the-body", person=person)                       # where the data lives: the run record and the sources use it
        who = (known.output or {}) if known.status == DONE else {}
        try:                                                                          # the answer depends on Intelligence: when it cannot run, say so plainly
            processed = take(self.intelligence, "the-intelligence", request=request, person=person, representative=who.get("representative"),
                             priorities=who.get("priorities"), cancelled=cancelled)
        except Exception as error:      # noqa: BLE001  the front door ends with a message, never a traceback
            processed = Step("the-intelligence", UNAVAILABLE, reason=f"{type(error).__name__}: {error}")
        thought = (processed.output or {}) if processed.status == DONE else {"answer": cannot_answer(processed.reason), "stopped": "unavailable"}
        stated = support(self.roles, "role-understanding", part_id="the-intelligence")
        log = [known, context, processed, stated]
        run = {"id": int(began * 1000), "request": request, "person": person, "sources": (context.output or {}).get("sources", []) if context.status == DONE else [],
               "steps": listing(log), "answer": thought.get("answer", ""),
               "attempts": thought.get("attempts", 0), "stopped": thought.get("stopped", "")}
        recorded = support(self.body, "the-body", method="record_run", run=run)
        audited = support(self.integrity, "system-integrity", method="audit_run", run=run)
        log += [recorded, audited]
        log.append(support(self.consciousness, "the-consciousness", method="learn", person=person, feedback=feedback))
        notes = list(audited.output or []) if audited.status == DONE else []
        notes += [str(line) for line in thought.get("notes") or ()]
        if thought.get("escalation"):
            decision = thought["escalation"]
            notes.append(stop_line(thought, decision))
        results = thought.get("results") or []
        return Result(input=request, seat="the-self", answer=str(thought.get("answer", "")), items=tuple(sources_of(results)), seconds=time.time() - began,
                      note="; ".join(notes), steps=tuple(listing(log)), stopped=str(thought.get("stopped", "")))

    def serve(self, person: str = "") -> Sequence[Result]:
        requests = take(self.consciousness, "the-consciousness", method="receive", person=person)
        return [self.respond(row["text"], row.get("person") or person) for row in (requests.output or [])]

    def act_unasked(self, schedules: Sequence[Mapping[str, Any]], now: str = "", person: str = "", candidates: Sequence[Mapping[str, Any]] = (),
                    stated: Optional[Mapping[str, Any]] = None, events: Sequence[Mapping[str, Any]] = ()) -> Sequence[Result]:
        """Responds to what is due, most important first: Consciousness gives the person's priorities (``stated``, else the ``priorities`` the Representative's
        preferences declare), Intelligence asks Proactivity what is due and Prioritization what matters first among it and ``candidates``, and each trigger,
        in that order, is responded to as a request. ``events`` are the items pulled through Body's Intake Sources."""
        known = take(self.consciousness, "the-consciousness", person=person)
        who = (known.output or {}) if known.status == DONE else {}
        said = stated if stated is not None else ((who.get("representative") or {}).get("preferences") or {}).get("priorities")
        due = take(self.intelligence, "the-intelligence", method="proactive", schedules=schedules, now=now, person=person, candidates=candidates,
                   stated=said, events=events)
        return [self.respond(trigger["request"], person) for trigger in (due.output or []) if trigger.get("request")]

    def order_asks(self, asks: Sequence[Mapping[str, Any]], person: str = "", stated: Optional[Mapping[str, Any]] = None, batch_limit: int = 0,
                   now: str = "") -> Mapping[str, Any]:
        """The asks waiting on a person, in the order to put them in front of that person: Consciousness decides which are worth an ask and Prioritization
        orders them; with a ``batch_limit`` only that many go forward and the rest are held with why. A part with no arm is a step that says so, and nothing is
        ordered by guess."""
        ordered = take(self.consciousness, "the-consciousness", method="order_asks", asks=list(asks), person=person, stated=stated, batch_limit=batch_limit, now=now)
        answer = (ordered.output or {}) if ordered.status == DONE else {}
        return {"asks": list(answer.get("asks") or []), "held": list(answer.get("held") or []), "not_asked": list(answer.get("not_asked") or []),
                "steps": listing([ordered])}

    def coverage(self) -> Mapping[str, Any]:
        found = take(self.assembler, "the-assembler")
        return found.output if found.status == DONE else {"built": [], "pending": {"the-assembler": found.reason}}

    def health(self) -> Mapping[str, Any]:
        """Whether the system stays generic and current: Integrity's audit and the areas of research World reports out of date."""
        audit = take(self.integrity, "system-integrity", terms=())
        stale = take(self.world, "the-world", method="stale_areas")
        return {"audit": audit.output if audit.status == DONE else None, "stale_areas": list(stale.output or []) if stale.status == DONE else None,
                "steps": listing([audit, stale])}
