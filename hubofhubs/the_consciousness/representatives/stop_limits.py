"""The limits on unasked iteration, resolved for one request: what the person stated, the policy and authority that bound the work, and whether what is missing needs a person.

Goal Completion's stop decision (``hubofhubs.the_intelligence.critical_thinking.goal_completion.stop_rule``) takes these as plain inputs and never reads a Consciousness
solution itself, so the same rule serves any consumer. They are resolved here, the way ``quality.resolve_profile`` resolves the quality profile: from the Representative
(the person's standing preference about iteration and the authority it carries), Guidance (the policy for this situation) and Judgment Calls (a decision to ask a person about
what is missing), and from what the person stated in this request. What the person stated outranks their standing preference; policy and authority only ever narrow
(the smallest cap wins, any prohibition holds); a person can always stop. Standard library only."""
from typing import Any, Dict, Mapping, Optional

STATED_KEYS = ("stop", "one_pass", "max_iterations", "keep_going_until", "until_reached")


def pick(source: Optional[Mapping[str, Any]], keys=STATED_KEYS) -> Dict[str, Any]:
    return {k: source[k] for k in keys if isinstance(source, Mapping) and source.get(k) not in (None, "", False)}


def smallest(*caps: Any) -> Optional[int]:
    found = [c for c in caps if isinstance(c, int) and not isinstance(c, bool) and c >= 0]
    return min(found) if found else None


def resolve_stop_limits(representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                        judgment: Optional[Mapping[str, Any]] = None, stated: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """``{"stated", "policy", "needs_human", "sources"}`` for one request. ``representative`` is a Representatives result (its ``preferences["iteration"]`` is the person's
    standing wish, its ``authority`` may carry ``max_iterations`` and ``iteration_exhausted``), ``guidance`` may carry ``iteration_policy`` (``forbids_iteration``,
    ``max_iterations``), ``judgment`` is a Judgment Calls result about what is missing (an ``ask`` to a person means it needs one) and ``stated`` is what the person said in this request."""
    preferences = ((representative or {}).get("preferences") or {}).get("iteration")
    authority = (representative or {}).get("authority") or {}
    policy_in = (guidance or {}).get("iteration_policy") or {}
    sources = []
    standing = pick(preferences)
    now = pick(stated)
    wish = {**standing, **now}
    if standing:
        sources.append("representative")
    if now:
        sources.append("stated")
    policy: Dict[str, Any] = {}
    cap = smallest(policy_in.get("max_iterations"), authority.get("max_iterations"))
    if cap is not None:
        policy["max_iterations"] = cap
    if policy_in.get("forbids_iteration") or authority.get("forbids_iteration"):
        policy["forbids_iteration"] = True
    if authority.get("iteration_exhausted"):
        policy["authority_exhausted"] = True
    if policy_in:
        sources.append("guidance")
    needs = ""
    if isinstance(judgment, Mapping) and str(judgment.get("decision") or "") == "ask":
        needs = str(judgment.get("reason") or "a decision only a person can make")
        sources.append("judgment-calls")
    return {"stated": wish, "policy": policy, "needs_human": needs, "sources": sources}
