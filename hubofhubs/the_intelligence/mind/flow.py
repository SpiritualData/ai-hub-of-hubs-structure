"""ACTION_OF_TOOL, failed_pieces, MindComposition, outside_of."""
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from esoi import implementation
from esoi.assemble import Lazy
from hubofhubs.the_intelligence.mind.context_intake.interface import ContextTaking
from hubofhubs.the_intelligence.mind.delegation.interface import Delegating
from hubofhubs.the_consciousness.judgment_calls.interface import JudgmentCalling
from hubofhubs.the_intelligence.mind.planner.interface import Planning
from hubofhubs.the_intelligence.mind.response_writer.interface import ResponseWriting
from hubofhubs.the_intelligence.nervous_system.interface import RiskWatching
from hubofhubs.the_intelligence.nervous_system.signals import RiskSignal
from hubofhubs.the_self.steps import DONE, Step, listing, skipped, take
from hubofhubs.the_self.steps import done


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
              cancelled: Optional[Callable[[], bool]] = None, instructions: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        authority = authority or {}
        log: List[Step] = [take(self.intake, "context-intake", request=request, prepared=prepared, outside=outside, instructions=instructions)]
        planned = take(self.planner, "planner", request=request, context=done(log[0]), target=target, guidance=guidance, unmet=unmet)
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
        return {"text": done(written) or "", "results": results, "pieces": list(done(planned) or []), "steps": listing(log)}


def outside_of(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """What the workers brought, in the shape Context Intake takes for the outside: their text and their sources."""
    return {"answer": "\n".join(str(r.get("text", "")) for r in results if r.get("text")), "items": [i for r in results for i in r.get("items") or ()]}
