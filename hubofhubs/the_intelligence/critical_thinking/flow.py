"""CriticalThinkingComposition."""
from typing import Any, Callable, Mapping, Optional, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_consciousness.representatives.quality import resolve_profile
from hubofhubs.the_intelligence.critical_thinking.decision_check.interface import DecisionChecking
from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import EsoiApplying
from hubofhubs.the_intelligence.critical_thinking.goal_completion.interface import GoalCompleting
from hubofhubs.the_intelligence.critical_thinking.pursuit import BoundedReplan
from hubofhubs.the_intelligence.critical_thinking.metric_translation.interface import MetricTranslating
from hubofhubs.the_intelligence.critical_thinking.response_quality.interface import ResponseJudging
from hubofhubs.the_self.steps import DONE, listing, skipped, take
from hubofhubs.the_self.steps import done


@implementation("critical-thinking", "composition")
class CriticalThinkingComposition:
    """A request becomes a target (Metric Translation, recorded as a spec through ESOI Application), and the response is held to it: Goal
    Completion says whether the goal was met, ``pursue`` keeps working while it is unmet, with the untried reads and within a budget, and Response Quality judges the response against the quality profile resolved for this request
    (the Representative's, Guidance's and Prioritization's, else the default), and Decision Check tests a draft decision with independent checks."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, metric: Lazy[MetricTranslating], esoi: Lazy[EsoiApplying], goal: Lazy[GoalCompleting], quality: Lazy[ResponseJudging],
                 decision: Lazy[DecisionChecking]):
        self.metric, self.esoi, self.goal, self.quality, self.decision = metric, esoi, goal, quality, decision

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

    def check_decision(self, draft: Any, binding: Any, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        """Has Decision Check test a draft decision (a pick among options, or a reply) with small independent checks within the binding's call cap; the result is the checked decision."""
        checked = take(self.decision, "decision-check", draft=draft, binding=binding, ask=ask)
        return {"decision": done(checked), "steps": listing([checked])}

    def pursue(self, goal: str, done_standard: str, draft: Any, attempt: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
               means: Sequence[Mapping[str, Any]] = (), budget: Optional[Mapping[str, Any]] = None,
               announce: Optional[Callable[[str], Any]] = None, check: Optional[Callable[[Any], Mapping[str, Any]]] = None) -> Mapping[str, Any]:
        """Keeps working on a draft whose goal is unmet: Goal Completion's verdict (or the ``check`` the consumer gives) is read, and while it is unmet
        the untried read-only ``means`` are offered to ``attempt`` within the ``budget``. The result holds the ``outcome`` to send, ``status``, ``met``,
        ``replans``, ``tried``, ``missing``, the one ``interim`` line if any, and a plain ``message`` for an unmet end. A write is never offered or accepted."""
        return dict(BoundedReplan(self.goal).pursue(goal, done_standard, draft, attempt, means, budget, announce, check))
