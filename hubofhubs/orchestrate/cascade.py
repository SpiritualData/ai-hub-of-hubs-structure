"""The planner cascade's structural half: which decisions a stronger model reviews, and how its verdict folds back.

The review prompt, the way a decision is described to the reviewer and every fallback sentence are the consumer's; this module
decides on the decision's own fields and never reads wording.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional

from .plan import PlanDecision

#: The confidence values a planner may report, weakest first.
CONFIDENCE_LEVELS = ("low", "medium", "high")

#: The actions an operator may name in the escalation setting as ``action:<name>``.
ESCALATABLE_ACTIONS = ("read", "answer", "deep", "confirm", "clarify", "tool")


def escalation_spec(spec: Optional[str]) -> Dict[str, FrozenSet[str]]:
    """Parse the escalation setting into the two signals it may name.

    Entries are a comma list of confidence levels ("low", "medium") and of actions written
    ``action:read``. An unrecognised entry is dropped rather than raising: a typo in an operator's
    setting should narrow what escalates, never break planning.

    WHY THERE ARE TWO SIGNALS, and why the ACTION one is the default. Self-reported confidence is
    the obvious signal and it is the one that did not work. Measured 2026-10-05 on 86 labelled
    hand-off cases: with the field required, a small model answered "high" on 84 of 86
    decisions, including 36 it got wrong, so confidence gated nothing (57 percent of its "high"
    decisions were correct, against 100 percent of its two "medium" ones, on an n of 2). A model
    that cannot tell a reachable request from an unreachable one also cannot tell that it cannot
    tell. The ACTION the planner chose is not a self-report, it is the decision itself, and it
    separates the error class cleanly: nearly every miss in that group is a "read" issued for work
    no read can reach, while a wrongly skipped read is rare. So the cheap, honest signal is
    structural. Confidence is kept because it costs one enum on a call already being made and
    might be calibrated on another model, but it is not what the default relies on.
    """
    levels: set = set()
    actions: set = set()
    for part in (spec or "").split(","):
        entry = part.strip().lower()
        if not entry:
            continue
        if entry.startswith("action:"):
            name = entry.split(":", 1)[1].strip()
            if name in ESCALATABLE_ACTIONS:
                actions.add(name)
        elif entry in CONFIDENCE_LEVELS:
            levels.add(entry)
    return {"levels": frozenset(levels), "actions": frozenset(actions)}


def should_escalate(decision: PlanDecision, spec: Any) -> bool:
    """True when this decision matches a signal the operator asked to have reviewed.

    ``spec`` is either the dict from ``escalation_spec`` or a bare set of confidence levels.
    No reported confidence means NO confidence-based escalation. That is the fail-safe that keeps
    a model which ignores the field, or a response that failed to parse, from escalating
    everything. The action signal has no such hole: a decision always has an action.
    """
    if isinstance(spec, dict):
        levels = spec.get("levels") or frozenset()
        actions = spec.get("actions") or frozenset()
    else:
        levels, actions = (spec or frozenset()), frozenset()
    if decision.action in actions:
        return True
    if not levels:
        return False
    return bool(decision.confidence) and decision.confidence in levels


def truncate_keep_both_ends(text: str, limit: int, marker: str = "\n...\n") -> str:
    """``text`` cut to ``limit`` characters by removing the MIDDLE, not either end.

    Both ends of a grounding block carry decision-relevant content (what exists at the top, what
    is reachable at the bottom), and a cut that silently drops one of them is worse than a
    smaller budget honestly spent.
    """
    if limit <= 0 or len(text) <= limit:
        return text if len(text) <= max(limit, 0) else ""
    room = limit - len(marker)
    if room <= 0:
        return text[:limit]
    head = room // 2
    return text[:head].rstrip() + marker + text[len(text) - (room - head):].lstrip()


def user_goal_fallback(cheap: PlanDecision, *, default_goal: str) -> str:
    """A goal for a reviewer that corrected the action without writing one.

    Never empty: a deep decision with no done-standard is rejected downstream, so a correction
    that would produce one is worse than no correction at all. ``default_goal`` is the consumer's sentence for when the
    decision carries nothing to build one from.
    """
    return (cheap.goal or cheap.deep_brief
            or (cheap.deferred_deep or {}).get("goal")
            or default_goal)


def apply_review(cheap: PlanDecision, raw: Optional[Dict[str, Any]], *, default_goal: str,
                 default_question: str) -> PlanDecision:
    """Fold a reviewer's verdict back onto the cheap decision.

    A reviewer that agrees, says nothing usable, or fails outright leaves the cheap decision
    EXACTLY as it was, reads included. Only a genuine correction replaces it, and even then the
    fields the reviewer did not speak to (the model tier, the deep difficulty rating, the target)
    are carried over rather than dropped. ``default_goal`` and ``default_question`` are the consumer's sentences for a
    correction that names no goal or no question.
    """
    if not isinstance(raw, dict):
        return cheap
    action = (raw.get("action") or "").strip().lower()
    if action not in ("read", "answer", "deep", "confirm"):
        return cheap
    rationale = (raw.get("rationale") or "").strip() or cheap.rationale
    if action == cheap.action and not (action == "answer" and bool(raw.get("hand_off"))
                                      and not cheap.deferred_deep):
        return cheap
    if action == "read":
        # The reviewer wants a read and the cheap model did not plan one, so there are no reads to
        # run. Answering is the honest fallback rather than an empty read step.
        if not cheap.reads:
            return PlanDecision(action="answer", rationale=rationale,
                                model_tier=cheap.model_tier, confidence=cheap.confidence)
        return PlanDecision(action="read", reads=cheap.reads, rationale=rationale,
                            model_tier=cheap.model_tier, confidence=cheap.confidence)
    goal = (raw.get("goal") or cheap.goal
            or (cheap.deferred_deep or {}).get("goal") or user_goal_fallback(cheap, default_goal=default_goal))
    brief = raw.get("deep_brief") or cheap.deep_brief or (cheap.deferred_deep or {}).get("brief")
    if action == "deep":
        return PlanDecision(action="deep", goal=goal, deep_brief=brief, rationale=rationale,
                            model_tier=cheap.model_tier, deep_difficulty=cheap.deep_difficulty,
                            deep_difficulty_reason=cheap.deep_difficulty_reason,
                            deep_target=cheap.deep_target, confidence=cheap.confidence)
    if action == "answer":
        deferred = None
        if raw.get("hand_off"):
            deferred = {"goal": goal, "brief": brief, "rationale": rationale}
        return PlanDecision(action="answer", rationale=rationale, deferred_deep=deferred,
                            model_tier=cheap.model_tier, deep_difficulty=cheap.deep_difficulty,
                            deep_difficulty_reason=cheap.deep_difficulty_reason,
                            deep_target=cheap.deep_target, confidence=cheap.confidence)
    question = (raw.get("confirm_question") or cheap.confirm_question or default_question)
    return PlanDecision(action="confirm", confirm_question=question, rationale=rationale,
                        model_tier=cheap.model_tier, confidence=cheap.confidence)
