"""Pursuing an unmet goal, a step of the Critical Thinking composition (``pursue``): what happens to a draft whose goal condition is unmet.

It checks the draft (through the check it is given, else Goal Completion) and, while the condition is unmet and read-only means
remain untried, offers them to ``attempt`` and checks again, within a budget: ``max_replans`` rounds and ``wall_seconds`` in all. Work estimated
longer than ``inline_seconds`` is not made to wait: the current response goes out first with one plain line saying the rest is still being worked on
(``announce`` is called once, with fixed text), and the work either continues inline or, when the budget says a ``background`` exists, is returned as the plan for
that follow-up. A write is never offered, and an attempt that reports one is discarded and recorded. When the condition cannot be met the result
says what was tried and that the rest is unconfirmed; the checker's own words (``missing``) are kept in the result for logs and never put in a response. Every decision reads structured facts (the verdict's boolean, the means, the budget, what ``attempt``
returned), never the words of a response. Standard library plus the hub
and ``esoi``."""
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_self.steps import done, take

DEFAULT_BUDGET: Dict[str, Any] = {"max_replans": 2, "wall_seconds": 90.0, "inline_seconds": 30.0, "background": False}
MET, MET_AFTER_REPLAN, UNMET_REPORTED, CONTINUING, UNMET_SENT_AS_IS = "met", "met_after_replan", "unmet_reported", "continuing", "unmet_sent_as_is"


def still_working_line() -> str:
    """The one plain line a long replan sends with the current response. It is fixed text: a verdict's reason or next action is a checker's
    working note (often a plan addressed to a worker), so it never reaches the person; it stays in the result's ``missing`` for logs and traces."""
    return "Still working on the part of your request I could not confirm yet. I will post what I find here."


def unmet_message(tried: Sequence[str]) -> str:
    """What was tried and that the rest is unconfirmed, from structured facts (the means tried) and fixed text only, for the same reason."""
    looked = "I tried " + ", ".join(tried) + "." if tried else "I had nothing further to try."
    return f"{looked} I could not confirm the rest of what you asked."


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
                line = still_working_line()
                if announce is not None and not interim:
                    announce(line)
                    interim = line
                if limits.get("background"):
                    return self.result(best, CONTINUING, False, replans, tried, missing, interim, message=line, **{"continue": {"means": names, "missing": missing}})
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
        out = self.result(best, UNMET_REPORTED, False, replans, tried, missing, interim, message=unmet_message(tried))
        out["ignored_writes"] = ignored
        return out
