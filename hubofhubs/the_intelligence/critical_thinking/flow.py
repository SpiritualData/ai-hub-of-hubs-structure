"""CriticalThinkingComposition."""
from typing import Any, Mapping, Optional
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_consciousness.representatives.quality import resolve_profile
from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import EsoiApplying
from hubofhubs.the_intelligence.critical_thinking.goal_completion.interface import GoalCompleting
from hubofhubs.the_intelligence.critical_thinking.metric_translation.interface import MetricTranslating
from hubofhubs.the_intelligence.critical_thinking.response_quality.interface import ResponseJudging
from hubofhubs.the_self.steps import DONE, listing, skipped, take
from hubofhubs.the_self.steps import done


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
