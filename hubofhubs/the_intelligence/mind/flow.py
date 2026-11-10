"""ACTION_OF_TOOL, failed_pieces, MindComposition, outside_of."""
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_intelligence.mind.context_intake.interface import ContextTaking
from hubofhubs.the_intelligence.mind.delegation.interface import Delegating
from hubofhubs.the_consciousness.judgment_calls.interface import JudgmentCalling
from hubofhubs.the_intelligence.mind.planner.interface import Planning
from hubofhubs.the_intelligence.mind.reference_resolver.interface import ReferenceResolving
from hubofhubs.the_intelligence.mind.request_router.interface import RequestRouting
from hubofhubs.the_intelligence.mind.planner.solution_pieces import tie
from hubofhubs.the_intelligence.mind.response_writer.interface import ResponseWriting
from hubofhubs.the_intelligence.nervous_system.interface import RiskWatching
from hubofhubs.the_intelligence.nervous_system.signals import RiskSignal
from hubofhubs.the_self.steps import DONE, Step, listing, skipped, support, take
from hubofhubs.the_self.steps import done


ACTION_OF_TOOL = {"web-search": "search", "the-science": "search", "read-files": "read", "file-editing": "update",
                  "connected-system-operations": "execute", "delegated-agent-sessions": "execute", "role-understanding": "read", "": "answer"}


def failed_pieces(results: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """The results of pieces that did not deliver: refused, failed, or a worker that said it did not meet its sub-goal."""
    return [r for r in results if r.get("refused") or r.get("error") or r.get("met") is False]


@implementation("the-mind", "composition")
class MindComposition:
    """The Mind for one request, in order: Context Intake, Resolve a Reference (each phrase the prepared context lists with its candidates), the Planner, Route a Request
    (what the plan asks of the system), Delegation and the Response Writer. A phrase that does not clearly name one candidate, and a request that cannot be acted on yet
    (the route is ``clarify``), mean no piece is handed on: nothing acts on a guess. Both steps are used only when handed their seats. Before a piece of work is handed on,
    the Nervous System signals how risky it is and Judgment Calls decides for this person; a piece that is not allowed is not delegated, and
    one that is asked about waits for the answer while the others go on. On a replan, Context Intake takes in what the workers brought last time. Given
    what each relevant solution's own pass found (``considered``), each planned piece is tied to the solution it serves and held to that solution's
    target, a needing solution no piece serves gets a piece of its own, and a worker that takes a brief gets that solution's generated prompt."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, intake: Lazy[ContextTaking], planner: Lazy[Planning], delegation: Lazy[Delegating], writer: Lazy[ResponseWriting],
                 watch: Lazy[RiskWatching], judgment: Lazy[JudgmentCalling], resolver: Lazy[ReferenceResolving] = None, router: Lazy[RequestRouting] = None):
        self.intake, self.planner, self.delegation, self.writer = intake, planner, delegation, writer
        self.watch, self.judgment = watch, judgment
        self.resolver, self.router = resolver, router

    def think(self, request: str, authority: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
              guidance: Optional[Mapping[str, Any]] = None, profile: Optional[Any] = None, prepared: Optional[Mapping[str, Any]] = None,
              unmet: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None, budget: Optional[Any] = None,
              cancelled: Optional[Callable[[], bool]] = None, instructions: Optional[Mapping[str, Any]] = None,
              considered: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        authority = authority or {}
        log: List[Step] = [support(self.intake, "context-intake", request=request, prepared=prepared, outside=outside, instructions=instructions)]
        resolved: List[Dict[str, Any]] = []
        for reference in [r for r in ((prepared or {}).get("references") or []) if isinstance(r, Mapping)] if self.resolver is not None else []:
            found = support(self.resolver, "resolve-a-reference", phrase=str(reference.get("phrase") or ""), candidates=list(reference.get("candidates") or []),
                         context=reference.get("context"))
            log.append(found)
            resolved.append({"phrase": str(reference.get("phrase") or ""), **dict(done(found) or {"outcome": "abstain", "id": "", "reason": found.reason})})
        unresolved = [r for r in resolved if r.get("outcome") != "match"]
        planned = take(self.planner, "planner", request=request, context=done(log[0]), target=target, guidance=guidance, unmet=unmet)
        log.append(planned)
        route = support(self.router, "route-a-request", request=request, context={"view": str(done(log[0]) or "")}) if self.router is not None else None
        if route is not None:
            log.append(route)
        clarify = route is not None and (done(route) or {}).get("route") == "clarify"
        allowed: List[Mapping[str, Any]] = []
        asked: List[Mapping[str, Any]] = []
        pieces = tie(done(planned) or [], considered) if considered else list(done(planned) or [])
        for piece in pieces:
            if unresolved or clarify:      # nothing acts on a guess: a phrase that named no one candidate, or a request not yet understood, hands nothing on
                asked.append({**piece, "refused": "reference not found: " + ", ".join(r["phrase"] for r in unresolved) if unresolved else "request needs clarifying"})
                continue
            digest = support(self.watch, "nervous-system", method="digest", user_message=request, step=1, max_steps=1,
                          plan_action=ACTION_OF_TOOL.get(str(piece.get("tool") or ""), "execute"), plan_goal=str(piece.get("piece", piece)))
            signal = support(self.watch, "nervous-system", digest=done(digest)) if digest.status == DONE else digest
            log.append(signal)
            if signal.status != DONE:      # a piece whose risk cannot be checked is not handed on
                asked.append({**piece, "refused": "risk could not be checked"})
                continue
            risk: RiskSignal = done(signal)
            decision = support(self.judgment, "judgment-calls", signal={"severity": risk.severity, "reason": risk.reason},
                            person=str(authority.get("person", "")))
            log.append(decision)
            if decision.status != DONE:      # no decision is not a yes: a piece nobody decided on is not handed on, like one whose risk was not checked
                asked.append({**piece, "refused": "no decision could be made"})
            elif (done(decision) or {}).get("decision") == "proceed":
                allowed.append(piece)
            else:
                asked.append({**piece, "refused": "asked", "decision": done(decision)})
        if not done(planned):
            log += [skipped("nervous-system", "no piece to check yet"), skipped("judgment-calls", "no piece to decide on yet")]
        handed = take(self.delegation, "delegation", pieces=allowed, authority=authority, budget=budget, cancelled=cancelled, context=done(log[0]))
        results = list(done(handed) or []) + [{"piece": str(p.get("piece", "")), "tool": str(p.get("tool", "")), "refused": p["refused"], "items": [], "text": ""}
                                              for p in asked]
        written = take(self.writer, "response-writer", results=results, profile=profile)
        log += [handed, written]
        return {"text": done(written) or "", "results": results, "pieces": pieces, "references": resolved, "route": done(route) if route is not None else None,
                "steps": listing(log)}


def outside_of(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """What the workers brought, in the shape Context Intake takes for the outside: their text and their sources."""
    return {"answer": "\n".join(str(r.get("text", "")) for r in results if r.get("text")), "items": [i for r in results for i in r.get("items") or ()]}
