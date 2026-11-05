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
from hubofhubs.the_self.steps import DONE, listing, take


def sources_of(results: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for result in results:
        for item in result.get("items") or ():
            seen.setdefault(str(item.get("url") or item.get("title")), dict(item))
    return list(seen.values())


@implementation("the-self", "composition")
class SelfComposition:
    """The Self responds as the whole. Its flow, in order: Consciousness represents the person, Body describes where the system's data lives,
    Intelligence processes the request with the Representative's authority (World's tools do the outside work from there), Role Understanding states what
    Intelligence is for, Body keeps the run record and Integrity audits it, and Consciousness learns from feedback when there is some. The result lists the step of every part and says
    which have no arm yet. World is asked, in ``health``, how current the research is. ``serve`` takes the waiting requests in through Consciousness; ``act_unasked`` responds to what Proactivity says is due.
    Every part, World included, is built on first use, so a seat that cannot be built is a pending step, not a failure of the rest, and a request that needs no key runs with none."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, world: Lazy[TakingIn], assembler: Lazy[WholeAssembling], integrity: Lazy[Genericity], body: Lazy[FormAndContext], intelligence: Lazy[InformationProcessing],
                 consciousness: Lazy[HumanAdapting], roles: Lazy[RoleUnderstanding]):
        self.world, self.assembler, self.integrity = world, assembler, integrity
        self.body, self.intelligence, self.consciousness, self.roles = body, intelligence, consciousness, roles

    def respond(self, request: str, person: str = "", feedback: Optional[Mapping[str, Any]] = None,
                cancelled: Optional[Callable[[], bool]] = None) -> Result:
        began = time.time()
        known = take(self.consciousness, "the-consciousness", person=person)
        context = take(self.body, "the-body", person=person)
        who = (known.output or {}) if known.status == DONE else {}
        processed = take(self.intelligence, "the-intelligence", request=request, person=person, representative=who.get("representative"),
                         priorities=who.get("priorities"), cancelled=cancelled)
        thought = (processed.output or {}) if processed.status == DONE else {}
        stated = take(self.roles, "role-understanding", part_id="the-intelligence")
        log = [known, context, processed, stated]
        run = {"id": int(began * 1000), "request": request, "person": person, "sources": (context.output or {}).get("sources", []) if context.status == DONE else [],
               "steps": listing(log), "answer": thought.get("answer", ""),
               "attempts": thought.get("attempts", 0), "stopped": thought.get("stopped", "")}
        recorded = take(self.body, "the-body", method="record_run", run=run)
        audited = take(self.integrity, "system-integrity", method="audit_run", run=run)
        log += [recorded, audited]
        log.append(take(self.consciousness, "the-consciousness", method="learn", person=person, feedback=feedback))
        notes = list(audited.output or []) if audited.status == DONE else []
        if thought.get("escalation"):
            decision = thought["escalation"]
            notes.append(f"stopped for {thought['stopped']}: {decision.get('decision')} {decision.get('to') or ''}".strip())
        results = thought.get("results") or []
        return Result(input=request, seat="the-self", answer=str(thought.get("answer", "")), items=tuple(sources_of(results)), seconds=time.time() - began,
                      note="; ".join(notes), steps=tuple(listing(log)))

    def serve(self, person: str = "") -> Sequence[Result]:
        requests = take(self.consciousness, "the-consciousness", method="receive", person=person)
        return [self.respond(row["text"], row.get("person") or person) for row in (requests.output or [])]

    def act_unasked(self, schedules: Sequence[Mapping[str, Any]], now: str = "", person: str = "") -> Sequence[Result]:
        due = take(self.intelligence, "the-intelligence", method="proactive", schedules=schedules, now=now)
        return [self.respond(trigger["request"], person) for trigger in (due.output or [])]

    def coverage(self) -> Mapping[str, Any]:
        found = take(self.assembler, "the-assembler")
        return found.output if found.status == DONE else {"built": [], "pending": {"the-assembler": found.reason}}

    def health(self) -> Mapping[str, Any]:
        """Whether the system stays generic and current: Integrity's audit and the areas of research World reports out of date."""
        audit = take(self.integrity, "system-integrity", terms=())
        stale = take(self.world, "the-world", method="stale_areas")
        return {"audit": audit.output if audit.status == DONE else None, "stale_areas": list(stale.output or []) if stale.status == DONE else None,
                "steps": listing([audit, stale])}
