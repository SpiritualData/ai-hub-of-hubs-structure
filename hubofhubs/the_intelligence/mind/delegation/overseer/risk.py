"""The nervous-system seat's engine: a minimal-intervention overseer that watches a run and sends at most one tiny signal.

A high-quality model reads a cheap, hard-capped digest of a run and answers with ONE of five signals. Nearly always it says
``proceed``. Any internal failure degrades to the safe default ``OverseerSignal("proceed", degraded=True)``, so wiring an
overseer in can never change a run's outcome except through an explicit signal. Nothing here raises.

The engine knows no consumer, no organisation and nothing of the orchestrator beyond the digest string. What a consumer
owns is data it passes in: the PROMPT (its consent rules and examples) as a ``render(digest) -> prompt`` callable. The hub
ships no prompt, so no consumer's policy lives here.

The five signals:
  - ``proceed``         the run is on track; do nothing (the overwhelming default).
  - ``redirect``        the plan is drifting off-subject or wasting reads; nudge with ONE hint.
  - ``answer_now``      enough has been gathered; stop reading and answer.
  - ``escalate_deep``   this genuinely needs real execution; hand off to deep work.
  - ``escalate_human``  a genuine human-only fork (identity, an irreversible or authorization decision, an ambiguity only the
    owner can resolve); hand off to a confirm instead of guessing.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from esoi import implementation

from hubofhubs.the_world.model_plumbing.model import STEP_JUDGE, plan_with_step
from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_world.model_plumbing.vendor_model_caller.interface import ModelCalling
from hubofhubs.the_intelligence.nervous_system.digest import build_digest, oneline
from hubofhubs.the_intelligence.nervous_system.signals import HIGH, LOW, MEDIUM, NONE, RiskSignal

# What an overseer verdict meant for risk: a step to stop and hand to a person is high, a step to change is medium, work that only needs a
# different worker is low, and the rest carries none. The overseer is a helper of Delegation, not an arm of the Nervous System.
VERDICT_SEVERITY = {"proceed": NONE, "answer_now": NONE, "escalate_deep": LOW, "redirect": MEDIUM, "escalate_human": HIGH}


def to_risk_signal(verdict: Any) -> RiskSignal:
    """The risk signal for an overseer verdict (an object with ``signal``, ``reason`` and ``degraded``)."""
    return RiskSignal(VERDICT_SEVERITY.get(getattr(verdict, "signal", NONE), NONE), getattr(verdict, "reason", "") or "",
                      bool(getattr(verdict, "degraded", False)))


@dataclass
class OverseerSignal:
    """One overseer decision. ``proceed`` is the do-nothing default.

    ``hint`` is only meaningful for ``redirect``: a single short course correction (kept under
    ~200 chars). ``reason`` is a one-sentence, user-safe explanation of the signal (may be surfaced
    as the overseer event's text), and is empty for a plain proceed.

    ``degraded`` distinguishes a REAL "proceed" verdict from a failure that fell back to proceed
    (provider error, non-dict response, unrecognized signal). The run treats both identically (do
    nothing), but the caller can use it to retry the consult at a different tier: a deployment
    whose overseer tier resolves to a model the wired provider cannot serve would otherwise have a
    permanently silent overseer that looks exactly like a healthy one.
    """
    signal: str = "proceed"    # "proceed" | "redirect" | "answer_now" | "escalate_deep" | "escalate_human"
    hint: str = ""              # only for redirect: ONE short course correction
    reason: str = ""             # one sentence, user-safe
    degraded: bool = False       # True when this proceed is a failure fallback, not a verdict


VALID_SIGNALS = ("proceed", "redirect", "answer_now", "escalate_deep", "escalate_human")


OVERSEE_TOOL: Dict[str, Any] = {
    "name": "oversee",
    "description": "Emit a single minimal-intervention signal about the run's direction.",
    "input_schema": {
        "type": "object",
        "properties": {
            # Descriptions here are DELIBERATELY bare mechanical minimums, not semantics: the full
            # behavioral meaning of each signal/field lives ONLY in OVERSEER_PROMPT's prose (see the
            # signal list + Rules section there). ClaudeCliProvider.plan() appends this ENTIRE schema
            # as inline JSON text on EVERY consultation (it cannot force native tool_choice), so any
            # duplication here is a real, repeated token cost, not a one-time one.
            "signal": {
                "type": "string",
                "enum": list(VALID_SIGNALS),
            },
            "hint": {
                "type": "string",
                "description": "only for redirect, under 200 chars",
            },
            "reason": {
                "type": "string",
                "description": "one short sentence",
            },
        },
        "required": ["signal"],
    },
}


def oversee_with(provider: Any, model: str, digest: str, render: Optional[Callable[[str], str]]) -> OverseerSignal:
    """Consult the overseer once and return its ``OverseerSignal``. Never raises.

    ONE structured ``provider.plan`` call; ``render(digest)`` is the consumer's prompt (its data, never the hub's). On ANY
    error, a non-dict response, or an unrecognized signal the result is the safe default ``OverseerSignal("proceed",
    degraded=True)``, so the run is never distorted or broken.
    """
    if render is None:
        return OverseerSignal("proceed", degraded=True)
    try:
        prompt = render(digest or "")
        raw = plan_with_step(provider, prompt, model=model, tool_schema=OVERSEE_TOOL, step=STEP_JUDGE)
        if not isinstance(raw, dict):
            return OverseerSignal("proceed", degraded=True)
        signal = str(raw.get("signal") or "").strip().lower()
        if signal not in VALID_SIGNALS:
            return OverseerSignal("proceed", degraded=True)
        hint = str(raw.get("hint") or "").strip()
        if signal != "redirect":
            hint = ""  # hint is only meaningful for a redirect
        hint = hint[:200]
        reason = str(raw.get("reason") or "").strip()
        return OverseerSignal(signal=signal, hint=hint, reason=reason)
    except Exception:  # noqa: BLE001 an overseer failure must degrade to proceed, never break
        return OverseerSignal("proceed", degraded=True)


class RunOverseer:
    """The digest-driven overseer: a helper of Delegation that watches a running worker and routes five ways (proceed, redirect, answer now, escalate to an
    agent session, escalate to a person). It is not an arm of the Nervous System, which sends one risk signal and does not route.

    ``render`` is the consumer's prompt as data: a callable turning a digest into the prompt text. It is the only place a
    consumer's consent rules and wording enter; the hub carries none.
    With no ``render`` there is no policy to apply, so every consultation is a degraded ``proceed`` and makes no model call.
    """
    REQUIRES = ()     # the model comes from the provider handed to oversee(), or the arm's own

    def __init__(self, render: Optional[Callable[[str], str]] = None, *, provider: ModelCalling = None):
        self.render = render
        self.provider = provider

    def watch(self, digest: str, model: str = "") -> RiskSignal:
        return to_risk_signal(self.oversee(self.provider, model, digest))

    def digest(self, **fields: Any) -> str:
        return build_digest(**fields)

    def oversee(self, provider: Any, model: str, digest: str) -> OverseerSignal:
        return oversee_with(provider, model, digest, self.render)
