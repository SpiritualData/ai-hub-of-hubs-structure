"""Goal Completion: says whether a goal's condition was met against its done-standard, as a mapping with ``met`` and ``reason``.

``evidence_standard`` reads two things and no prose judgment: the outcome's declared coverage (a ``coverage`` record from the worker's own
bookkeeping, through ``done_evidence``: a set that was not fully processed is not met), and the done-standard's requirements (each a
checkable phrase that the outcome's text must contain). An outcome that is empty, or that says a step was refused, is not met. Pure
functions, no model call. ``decide_stop`` answers the second question a flow asks (iterate again?): the two baselines above, the pragmatic rule, an independent reviewer and a fast-tier model
judgment below, the rule itself in ``stop_rule``. Standard library plus the hub and ``esoi``."""
import json
from typing import Any, Callable, List, Mapping, Optional

from esoi import Lazy, implementation

from hubofhubs.the_intelligence.critical_thinking.goal_completion import stop_rule
from hubofhubs.the_intelligence.critical_thinking.goal_completion.done_evidence import clean_requirements, coverage_gap, render_coverage_line
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing


def outcome_text(outcome: Any) -> str:
    if isinstance(outcome, Mapping):
        return str(outcome.get("text") or outcome.get("output") or "")
    return str(outcome or "")


def requirements_of(done_standard: str) -> List[str]:
    """The requirements a done-standard states: its ``;``-separated clauses after a ``must contain`` or ``includes`` (checkable phrases), else none."""
    for marker in ("must contain", "includes", "must include"):
        if marker in done_standard.lower():
            tail = done_standard[done_standard.lower().index(marker) + len(marker):]
            return clean_requirements([part.strip(" .:") for part in tail.split(";")])
    return []


@implementation("goal-completion", "evidence_standard")
class EvidenceStandard:
    """Met when the outcome says something, declares no coverage gap, was not refused, and holds every requirement of the done-standard."""
    REQUIRES = ()     # pure functions

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]:
        text = outcome_text(outcome)
        if isinstance(outcome, Mapping) and outcome.get("refused"):
            return {"met": False, "reason": f"the work was refused: {outcome['refused']}"}
        if isinstance(outcome, Mapping) and outcome.get("error"):
            return {"met": False, "reason": f"the work failed: {outcome['error']}"}
        if not text.strip():
            return {"met": False, "reason": "the outcome is empty"}
        raw = outcome.get("coverage") if isinstance(outcome, Mapping) else None
        if coverage_gap(raw) is not None:
            return {"met": False, "reason": render_coverage_line(raw)}
        missing = [r for r in requirements_of(done_standard) if r.lower() not in text.lower()]
        if missing:
            return {"met": False, "reason": "the outcome does not hold: " + "; ".join(missing)}
        return {"met": True, "reason": "the outcome is present, complete as declared, and holds every requirement"}

    def decide_stop(self, history: Mapping[str, Any]) -> Mapping[str, Any]:
        """The stop-only-when-met alternative: continue until the last verdict is met, whatever it costs (the baseline the pragmatic rule has to beat)."""
        return stop_rule.until_met(history)


@implementation("goal-completion", "nonempty")
class NonEmpty:
    """Met when the outcome is not empty: what a flow with no completion check implies. The bound the evidence standard has to beat."""
    REQUIRES = ()     # nothing

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]:
        text = outcome_text(outcome)
        if isinstance(outcome, Mapping) and (outcome.get("error") or outcome.get("refused")):
            return {"met": False, "reason": "the work failed or was refused"}
        return {"met": bool(text.strip()), "reason": "the outcome is not empty" if text.strip() else "the outcome is empty"}

    def decide_stop(self, history: Mapping[str, Any]) -> Mapping[str, Any]:
        """The fixed-iteration-cap alternative: a set number of iterations whatever the evidence says (the baseline)."""
        return stop_rule.fixed_cap(history)


# --- the stop-decision arms beyond the two baselines ---------------------------------------------------------------------------------
# All three keep the verdict of ``evidence_standard`` for ``check`` and differ in ``decide_stop``. ``independent_review`` is an arm and not a stage because the metric must be
# able to rank it against the rule that trusts the check; ``fast_tier_stop`` calls a model, so it is ``PAID``.


@implementation("goal-completion", "pragmatic_stop")
class PragmaticStop(EvidenceStandard):
    """Stops when the goal is met, when the person or policy says so, when a ceiling is reached, and otherwise only while the last iteration's gain is worth its cost."""
    REQUIRES = ()     # pure functions

    def decide_stop(self, history: Mapping[str, Any]) -> Mapping[str, Any]:
        return stop_rule.decide(history)


@implementation("goal-completion", "independent_review")
class IndependentReview(EvidenceStandard):
    """A second pass: the last outcome is read without the worker's claim or the verdict it came with, and the rule runs on that reading."""
    REQUIRES = ()     # pure functions

    def decide_stop(self, history: Mapping[str, Any]) -> Mapping[str, Any]:
        its = stop_rule.iterations_of(history)
        if not its:
            return stop_rule.decide(history)
        last = its[-1]
        outcome = last.get("outcome")
        standard = str(history.get("done_standard") or "")
        if outcome is None or not standard.strip():
            met = None          # nothing to read it against: the verdict it was handed stands, the claim never does
        else:
            met = bool(self.check(str(history.get("goal") or ""), standard, outcome)["met"])
        return stop_rule.decide(history, met=met)


PROMPT = """You decide whether an AI that has already worked on a goal should iterate again without being asked. Reply with JSON only: {{"decision": one of continue, stop_met, stop_good_enough, stop_not_worth_it, ask, "reason": one sentence}}.
Rules: stop_met when the verified check says the goal is met or the next milestone is reached; what the person stated (one pass, keep going until something) outranks the default; policy and authority bound the work; ask when what is missing only a person can supply or the person asked to keep going and a ceiling is reached; stop_good_enough at a ceiling, a policy or a person limit, say what is left; stop_not_worth_it on a plateau, an oscillation, a regress or when the cost of another iteration exceeds the gain it is expected to bring; continue only while the last iteration's gain is worth its cost. Ignore what the worker claims about itself; trust only the checks.
History:
{history}
"""


@implementation("goal-completion", "fast_tier_stop")
class FastTierStop(EvidenceStandard):
    """Asks the fast tier for the decision on the history; a reply that is not one of the five decisions falls back to the rule."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "fast", ask: Optional[Callable[[str], str]] = None):
        self.plumbing, self.tier, self.injected = plumbing, tier, ask

    def decide_stop(self, history: Mapping[str, Any]) -> Mapping[str, Any]:
        prompt = PROMPT.format(history=json.dumps(history, sort_keys=True, default=str)[:6000])
        try:
            raw = self.injected(prompt) if self.injected is not None else self.plumbing.ask(prompt, self.tier)
            text = str(raw or "")
            data = json.loads(text[text.index("{"):text.rindex("}") + 1])
            decision = str(data.get("decision") or "")
        except Exception:  # noqa: BLE001 -- a failed or unreadable call is no opinion
            decision = ""
        if decision not in stop_rule.DECISIONS:
            return dict(stop_rule.decide(history), code="fallback_rule")
        return stop_rule.result(decision, "model", str(data.get("reason") or ""), {"iterations": len(stop_rule.iterations_of(history))},
                                stop_rule.what_is_left(history) if decision in (stop_rule.STOP_GOOD_ENOUGH, stop_rule.STOP_NOT_WORTH_IT) else "")
