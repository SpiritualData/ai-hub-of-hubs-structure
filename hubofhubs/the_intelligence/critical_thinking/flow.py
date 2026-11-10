"""CriticalThinkingComposition."""
from typing import Any, Callable, Mapping, Optional, Sequence
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_consciousness.representatives.quality import resolve_profile
from hubofhubs.the_consciousness.representatives.stop_limits import resolve_stop_limits
from hubofhubs.the_intelligence.critical_thinking.decision_check.interface import DecisionChecking
from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import EsoiApplying
from hubofhubs.the_intelligence.critical_thinking.goal_completion.interface import GoalCompleting
from hubofhubs.the_intelligence.critical_thinking.goal_completion.done_evidence import measure as measure_increment
from hubofhubs.the_intelligence.critical_thinking.metric_upkeep.interface import MetricUpkeeping
from hubofhubs.the_intelligence.critical_thinking.pursuit import REFUSED_BOOKKEEPING, BoundedReplan, choose_increment, doable_by_ai
from hubofhubs.the_intelligence.critical_thinking.metric_translation.interface import MetricTranslating
from hubofhubs.the_intelligence.critical_thinking.response_quality.interface import ResponseJudging
from hubofhubs.the_intelligence.critical_thinking.solution_passes.interface import SolutionConsidering
from hubofhubs.the_intelligence.critical_thinking.solution_passes.depth import build_out
from hubofhubs.the_intelligence.critical_thinking.solution_passes.write_back import combined_check, proposals_of
from hubofhubs.the_self.steps import DONE, NO_ARM, PENDING, Step, listing, skipped, take
from hubofhubs.the_self.steps import done


@implementation("critical-thinking", "composition")
class CriticalThinkingComposition:
    """A request becomes a target (Metric Translation, recorded as a spec through ESOI Application), and the response is held to it: Goal
    Completion says whether the goal was met, ``pursue`` keeps working while it is unmet, with the untried reads and within a budget, and Response Quality judges the response against the quality profile resolved for this request
    (the Representative's, Guidance's and Prioritization's, else the default), and Decision Check tests a draft decision with independent checks. ``progress``
    composes one measurable step on a milestone: Metric Upkeep, then the increment rule, the before reading, the work, ``pursue`` (which refuses a bookkeeping-only
    result) and the after reading. ``consider`` gives each solution the request concerns its own pass through Solution Passes, ``check_pieces``
    holds each plan piece to its own solution's target through Goal Completion and checks that the pieces still combine, and ``write_back`` has ESOI
    Application record what was learned (knowledge items, results, candidates) so the next request's prompts carry it."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, metric: Lazy[MetricTranslating], esoi: Lazy[EsoiApplying], goal: Lazy[GoalCompleting], quality: Lazy[ResponseJudging],
                 decision: Lazy[DecisionChecking], upkeep: Lazy[MetricUpkeeping], consideration: Lazy[SolutionConsidering] = None):
        self.metric, self.esoi, self.goal, self.quality, self.decision, self.metric_upkeep = metric, esoi, goal, quality, decision, upkeep
        self.consideration = consideration

    def consider(self, request: str, briefs: Mapping[str, Any], own_passes: Optional[Mapping[str, Callable[..., Mapping[str, Any]]]] = None,
                 limits: Optional[Mapping[str, int]] = None, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        """One pass per solution the request concerns, then the scopes above and the dependents (Solution Passes)."""
        found = take(self.consideration, "solution-passes", request=request, briefs=briefs, own_passes=own_passes, limits=limits, ask=ask) \
            if self.consideration is not None else Step("solution-passes", PENDING, reason=NO_ARM)
        return {**dict(done(found) or {}), "steps": listing([found])}

    def check_pieces(self, results: Sequence[Mapping[str, Any]], considered: Mapping[str, Any]) -> Mapping[str, Any]:
        """Each piece tied to a solution is checked against that solution's own target (Goal Completion), and the parent passes' findings say whether
        the pieces still combine: ``pieces`` (solution, met, reason, the target it was held to) and ``combined`` (``met``, ``reasons``)."""
        findings = {f["solution_id"]: f for f in considered.get("findings") or []}
        pieces, log = [], []
        for result in results:
            finding = findings.get(str(result.get("solution_id") or ""))
            if finding is None:
                continue
            target = finding.get("target") or {}
            standard = str(target.get("done_when") or finding.get("needs") or "")
            met = take(self.goal, "goal-completion", goal=str(result.get("piece") or ""), done_standard=standard,
                       outcome={"text": str(result.get("text") or ""), "refused": str(result.get("refused") or ""), "error": str(result.get("error") or "")})
            log.append(met)
            verdict = done(met) or {}
            pieces.append({"solution_id": finding["solution_id"], "piece": str(result.get("piece") or ""), "metric_id": str(target.get("metric_id") or ""),
                           "value": str(target.get("value") or ""), "done_standard": standard, "met": verdict.get("met"), "reason": str(verdict.get("reason") or "")})
        return {"pieces": pieces, "combined": combined_check(pieces, considered), "steps": listing(log)}

    def build_out(self, item: Mapping[str, Any], work: Callable[[Mapping[str, Any]], str], check: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
                  split: Optional[Callable[..., Sequence[Mapping[str, Any]]]] = None, combine: Optional[Callable[..., str]] = None,
                  budget: Optional[Mapping[str, int]] = None, base: Optional[str] = None) -> Mapping[str, Any]:
        """Depth for a piece that falls short of its own solution's metric: its check returns it, it is split into the sub-pieces its missing
        requirements need (each with its own sub-prompt, done by ``work``), the parts are combined and checked again against the whole rubric,
        within ``budget`` (calls, depth, width). See ``solution_passes.depth``."""
        return build_out(item, work, check, split, combine, budget, base)

    def write_back(self, considered: Mapping[str, Any], checked: Optional[Mapping[str, Any]] = None, today: str = "",
                   apply: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None) -> Mapping[str, Any]:
        """ESOI Application records what the request taught each solution: the knowledge items its pass proposed, the result of each checked piece
        and the candidates it named, sourced, at the records location the seat (or ``apply``) writes to. Returns ``proposed`` and ``applied``."""
        proposed = proposals_of(considered, checked or {}, today)
        applied, log = [], []
        for change in proposed:
            if apply is not None:
                applied.append({"change": change, "result": dict(apply(change) or {})})
                continue
            step = take(self.esoi, "esoi-application", change=change)
            log.append(step)
            applied.append({"change": change, "result": dict(done(step) or {"applied": False, "reason": step.reason})})
        return {"proposed": proposed, "applied": applied, "steps": listing(log)}

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None, solutions: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]:
        extra = {"solutions": list(solutions)} if solutions else {}       # each relevant solution's own target, from its own metric
        found = take(self.metric, "metric-translation", request=request, parent=parent, **extra)
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

    def decide_stop(self, history: Mapping[str, Any], representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                    judgment: Optional[Mapping[str, Any]] = None, stated: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        """Whether iteration the person did not ask for should go on (Goal Completion's ``decide_stop``), with the limits resolved for this request: what the person
        stated outranks their standing preference, Guidance's policy and the Representative's authority bound it, and a Judgment Calls decision to ask a person makes
        what is missing a human's. Only hub-initiated iteration is judged; the person's own session is never stopped here. Returns ``decision`` (None when Goal
        Completion has no arm), ``limits`` and the steps."""
        limits = resolve_stop_limits(representative, guidance, judgment, stated)
        full = dict(history, stated={**dict(history.get("stated") or {}), **limits["stated"]}, policy={**dict(history.get("policy") or {}), **limits["policy"]},
                    needs_human=limits["needs_human"] or history.get("needs_human") or "")
        found = take(self.goal, "goal-completion", method="decide_stop", history=full)
        return {"decision": done(found), "limits": limits, "steps": listing([found])}

    def check_decision(self, draft: Any, binding: Any, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        """Has Decision Check test a draft decision (a pick among options, or a reply) with small independent checks within the binding's call cap; the result is the checked decision."""
        checked = take(self.decision, "decision-check", draft=draft, binding=binding, ask=ask)
        return {"decision": done(checked), "steps": listing([checked])}

    def pursue(self, goal: str, done_standard: str, draft: Any, attempt: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
               means: Sequence[Mapping[str, Any]] = (), budget: Optional[Mapping[str, Any]] = None,
               announce: Optional[Callable[[str], Any]] = None, check: Optional[Callable[[Any], Mapping[str, Any]]] = None,
               progress: bool = False) -> Mapping[str, Any]:
        """Keeps working on a draft whose goal is unmet: Goal Completion's verdict (or the ``check`` the consumer gives) is read, and while it is unmet
        the untried read-only ``means`` are offered to ``attempt`` within the ``budget``. The result holds the ``outcome`` to send, ``status``, ``met``,
        ``replans``, ``tried``, ``missing``, the one ``interim`` line if any, and a plain ``message`` for an unmet end. A write is never offered or accepted.
        With ``progress`` (the turn's resolved intent is progress on a milestone or goal) a draft with no AI increment measured before is refused."""
        return dict(BoundedReplan(self.goal).pursue(goal, done_standard, draft, attempt, means, budget, announce, check, progress))

    def upkeep(self, spec: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], readers: Optional[Mapping[str, Any]] = None, today: str = "",
               ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        """Metric Upkeep on the milestone's metrics: the action taken for each (read, propose a source, define an intermediate)."""
        kept = take(self.metric_upkeep, "metric-upkeep", spec=spec, metrics=metrics, readers=readers, today=today, ask=ask)
        return {"actions": list(done(kept) or []), "steps": listing([kept])}

    def progress(self, milestone: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], work_items: Sequence[Mapping[str, Any]],
                 work: Callable[[Mapping[str, Any]], Mapping[str, Any]], judge: Optional[Callable[[Optional[str], str], Any]] = None,
                 means: Sequence[Mapping[str, Any]] = (), readers: Optional[Mapping[str, Any]] = None, today: str = "",
                 ask: Optional[Callable[[str], str]] = None, kept: Any = None) -> Mapping[str, Any]:
        """One measurable step on a milestone. Metric Upkeep keeps its metrics able to show progress (and adds an intermediate metric when the milestone's
        own moves only through a person); the increment rule picks the first rung that applies from the structured work items; the BEFORE is measured on what
        is already kept (``kept``: an earlier version, None scores 0); ``work(increment) -> {"artifact", "evidence_ref", "asks"}`` does it (inline here; a
        background increment is returned as a plan); ``pursue`` refuses a result with no increment; the AFTER is measured by ``judge`` (never the writer).
        The result holds ``increment``, ``before``, ``after``, ``artifact``, ``asks`` (at most one person-only step, added to the increment), ``status`` and the steps."""
        work_item = next((w for w in work_items if str(w.get("kind") or "") == "deliverable" and doable_by_ai(w, means, list(milestone.get("records") or []))), None)
        if work_item is not None and not milestone.get("ai_work"):
            # An intermediate metric counts units of the work the AI will do, so upkeep is told what that work is and the measure and the work cannot drift apart.
            milestone = dict(milestone, ai_work=str(work_item.get("name") or "") + (" (each unit must: " + "; ".join(map(str, work_item.get("requirements") or [])) + ")"
                                                                                    if work_item.get("requirements") else ""))
        upkept = self.upkeep(milestone, metrics, readers, today, ask)
        increment = choose_increment(milestone, upkept["actions"], work_items, means)
        if increment is None:
            return {"status": "no_increment", "increment": None, "actions": upkept["actions"], "steps": upkept["steps"],
                    "message": "no AI-doable work item or reading applies; the work items need decomposing again"}
        child = next((a.get("child_metric") for a in upkept["actions"] if isinstance(a.get("child_metric"), Mapping)
                      and str(a["child_metric"].get("id") or "") == increment.measure_id), None)
        if child and child.get("rubric") and not increment.requirements:
            increment.requirements = [str(r) for r in child["rubric"]]       # a work item with no requirements of its own is held to the metric's rubric
        reader = (lambda: increment.item.get("reading") or {}) if increment.method == "read" else None
        # A reading's before is the value the record held before it was read (unmeasured is 0), its after the reading itself: one measure against itself.
        held = (lambda: {"value": increment.item.get("previous") or 0, "as_of": today}) if increment.method == "read" else None
        before = measure_increment(increment, kept, judge, held or reader, today, total=self.total_of(upkept["actions"]))
        increment.before = before.value if before.value is not None else 0.0
        if increment.size == "background":
            return {"status": "continuing", "increment": increment.to_dict(), "before": before.to_dict(), "actions": upkept["actions"], "steps": upkept["steps"]}
        made = dict(work(increment.to_dict()) or {})
        produced = bool(made.get("artifact")) and (made.get("artifact") != kept or increment.method == "read")
        draft = {"text": str(made.get("artifact") or ""), "increments": [increment.to_dict()] if produced else [], "writes": list(made.get("writes") or [])}
        pursued = self.pursue(str(milestone.get("name") or ""), str(milestone.get("done_when") or ""), draft, check=lambda outcome: {"met": True}, progress=True)
        if pursued.get("status") == REFUSED_BOOKKEEPING:
            return {"status": REFUSED_BOOKKEEPING, "increment": increment.to_dict(), "before": before.to_dict(), "actions": upkept["actions"], "steps": upkept["steps"]}
        after = measure_increment(increment, made.get("artifact"), judge, reader, today, str(made.get("evidence_ref") or ""), total=before.total)
        asks = [a for a in made.get("asks") or [] if str(a).strip()][:1]
        return {"status": "measured", "increment": increment.to_dict(), "before": before.to_dict(), "after": after.to_dict(), "artifact": made.get("artifact"),
                "asks": asks, "actions": upkept["actions"], "steps": upkept["steps"]}

    @staticmethod
    def total_of(actions: Sequence[Mapping[str, Any]]) -> Optional[int]:
        """The total an intermediate metric is counted out of, when upkeep defined or found one."""
        for action in actions:
            child = action.get("child_metric")
            if isinstance(child, Mapping) and str(child.get("total") or "").isdigit():
                return int(child["total"])
        return None
