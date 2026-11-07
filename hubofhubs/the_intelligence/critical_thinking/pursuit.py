"""Pursuing an unmet goal, a step of the Critical Thinking composition (``pursue``): what happens to a draft whose goal condition is unmet.

It checks the draft (through the check it is given, else Goal Completion) and, while the condition is unmet and read-only means
remain untried, offers them to ``attempt`` and checks again, within a budget: ``max_replans`` rounds and ``wall_seconds`` in all. Work estimated
longer than ``inline_seconds`` is not made to wait: the work either continues inline or, when the budget says a ``background`` exists, is returned as the plan for
that follow-up. A write is never offered, and an attempt that reports one is discarded and recorded. No line is added to the response in any outcome (no "still working",
no list of what was tried, no "could not confirm"): the response says what it holds and the reply's own grounding says what it lacks. The result's ``tried`` and the checker's
own words (``missing``) are kept for logs and never put in a response. Every decision reads structured facts (the verdict's boolean, the means, the budget, what ``attempt``
returned), never the words of a response. A draft whose structured outcome is a question to the person (the check's ``awaiting_person`` flag) is a
terminal, satisfied state: the goal condition of a cut-off or ambiguous message is that the person supplies the missing piece, so nothing is pursued,
announced or queued and no line is added. Standard library plus the hub
and ``esoi``."""
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_self.steps import done, take

DEFAULT_BUDGET: Dict[str, Any] = {"max_replans": 2, "wall_seconds": 90.0, "inline_seconds": 30.0, "background": False}
MET, MET_AFTER_REPLAN, UNMET_REPORTED, CONTINUING, UNMET_SENT_AS_IS = "met", "met_after_replan", "unmet_reported", "continuing", "unmet_sent_as_is"
AWAITING_PERSON = "awaiting_person"


def plain_text(outcome: Any) -> str:
    if isinstance(outcome, Mapping):
        return str(outcome.get("text") or outcome.get("output") or "")
    return str(outcome or "")


class Verdicts:
    """The check of a draft: the check it is given, else the Goal Completion seat."""

    def __init__(self, seat: Any, goal: str, done_standard: str, check: Optional[Callable[[Any], Mapping[str, Any]]]):
        self.seat, self.goal, self.done_standard, self.check = seat, goal, done_standard, check

    def of(self, outcome: Any) -> Mapping[str, Any]:
        if self.check is not None:
            return self.check(outcome)
        found = take(self.seat, "goal-completion", goal=self.goal, done_standard=self.done_standard, outcome=outcome)
        return done(found) or {"met": False, "reason": "the goal could not be checked: " + (found.reason or "no checker")}


class BoundedReplan:
    """Replans with the untried reads before sending, within a budget; sends the current response and says the rest is still being worked on when the work is long; reports what was tried and what is missing when the condition cannot be met."""

    def __init__(self, goal: Any = None):
        self.goal = goal      # the Goal Completion seat, used when no check is given

    def result(self, outcome: Any, status: str, met: bool, replans: int, tried: List[str], missing: str, interim: str, **more: Any) -> Dict[str, Any]:
        return dict({"outcome": outcome, "status": status, "met": met, "replans": replans, "tried": tried, "missing": missing, "interim": interim,
                     "message": "" if met else more.pop("message", ""), "ignored_writes": []}, **more)

    def pursue(self, goal: str, done_standard: str, draft: Any, attempt: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
               means: Sequence[Mapping[str, Any]] = (), budget: Optional[Mapping[str, Any]] = None,
               announce: Optional[Callable[[str], Any]] = None, check: Optional[Callable[[Any], Mapping[str, Any]]] = None) -> Mapping[str, Any]:
        limits = dict(DEFAULT_BUDGET, **dict(budget or {}))
        started = time.monotonic()
        elapsed = limits.get("elapsed") or (lambda: time.monotonic() - started)
        verdicts = Verdicts(self.goal, goal, done_standard, check)
        verdict = verdicts.of(draft)
        if verdict.get("met"):
            return self.result(draft, MET, True, 0, [], "", "")
        if verdict.get("awaiting_person") is True:
            return self.result(draft, AWAITING_PERSON, True, 0, [], "", "")
        best, tried, interim, replans, ignored = draft, [], "", 0, []
        reads = [m for m in means if str(m.get("kind", "read")) == "read"]
        while attempt is not None and replans < int(limits["max_replans"]):
            untried = [m for m in reads if str(m.get("name")) not in tried]
            if not untried:
                break
            names = [str(m.get("name")) for m in untried]
            estimate = sum(float(m.get("cost_seconds") or 0.0) for m in untried)
            missing = str(verdict.get("reason") or "")
            if estimate > float(limits["wall_seconds"]) - float(elapsed()):
                break
            if estimate > float(limits["inline_seconds"]):
                if limits.get("background"):
                    return self.result(best, CONTINUING, False, replans, tried, missing, interim, **{"continue": {"means": names, "missing": missing}})
            replans += 1
            step = attempt({"means": names, "missing": missing, "replan": replans, "read_only": True})
            if step.get("writes"):
                ignored.append(list(step["writes"]))      # a replan never writes: what it reports is not trusted
                break
            tried.extend(str(n) for n in (step.get("means_used") or names))
            if plain_text(step.get("outcome")).strip():
                best = step["outcome"]
            verdict = verdicts.of(best)
            if verdict.get("met"):
                return self.result(best, MET_AFTER_REPLAN, True, replans, tried, "", interim)
        missing = str(verdict.get("reason") or "")
        out = self.result(best, UNMET_REPORTED, False, replans, tried, missing, interim)
        out["ignored_writes"] = ignored
        return out
