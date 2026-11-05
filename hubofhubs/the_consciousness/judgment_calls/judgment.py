"""Judgment Calls: decides, for one person, what to do with a risk signal (or with a flow that ran out of budget or authority): proceed, ask
or decline. It also owns the **ask timing**: whether the ask blocks (``sync``) or waits (``async``), whether it is batched with other asks,
and what may continue meanwhile. The decision may be to a human, another agent or a delegate (``to``). A person's own policy comes from
their Representative's ``authority["ask"]``; the default policy proceeds on none and low, asks on medium and high, and declines nothing.
Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

from hubofhubs.the_intelligence.nervous_system.signals import HIGH, LOW, MEDIUM, NONE, RANK

PROCEED, ASK, DECLINE = "proceed", "ask", "decline"
DEFAULT_POLICY = {"proceed_up_to": LOW, "decline_from": None, "ask_to": "human"}


def severity_of(signal: Mapping[str, Any]) -> str:
    found = str(signal.get("severity") or "")
    if found in RANK:
        return found
    return MEDIUM      # a signal that names no severity is an unchecked step, and an unchecked step is not a safe one


def timing(severity: str) -> Dict[str, Any]:
    """A medium risk waits and is batched with other asks while safe work continues; a high one blocks, alone."""
    if severity == HIGH:
        return {"mode": "sync", "batch": False, "continue": []}
    return {"mode": "async", "batch": True, "continue": ["pieces that do not depend on the answer"]}


@implementation("judgment-calls", "severity_policy")
class SeverityPolicy:
    """Proceeds up to the person's own severity, declines from the severity they set (when they set one) and asks in between, to whom they
    named, with the timing the severity calls for. A flow that stopped for budget or authority is always asked about."""
    REQUIRES = ()     # policies are a constructor argument

    def __init__(self, policies: Optional[Mapping[str, Mapping[str, Any]]] = None):
        self.policies = dict(policies or {})

    def decide(self, signal: Mapping[str, Any], person: str = "", context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        policy = {**DEFAULT_POLICY, **dict(self.policies.get(person) or {})}
        reason = str(signal.get("reason") or "")
        stopped = str((context or {}).get("stopped") or "")
        severity = MEDIUM if stopped and RANK[severity_of(signal)] < RANK[MEDIUM] else severity_of(signal)
        if stopped:
            reason = reason or f"the request ran out of {stopped}"
        if policy["decline_from"] and RANK[severity] >= RANK[policy["decline_from"]]:
            return {"decision": DECLINE, "to": "", "timing": {}, "reason": reason, "severity": severity}
        if not stopped and RANK[severity] <= RANK[policy["proceed_up_to"]]:
            return {"decision": PROCEED, "to": "", "timing": {}, "reason": reason, "severity": severity}
        return {"decision": ASK, "to": policy["ask_to"], "timing": timing(severity), "reason": reason, "severity": severity}


@implementation("judgment-calls", "ask_every_time")
class AskEveryTime:
    """Asks about every step that carries any risk, blocking, whoever the person is: the fixed rule the per-person policy has to beat."""
    REQUIRES = ()     # nothing

    def decide(self, signal: Mapping[str, Any], person: str = "", context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        severity = severity_of(signal)
        if severity == NONE and not (context or {}).get("stopped"):
            return {"decision": PROCEED, "to": "", "timing": {}, "reason": "", "severity": severity}
        return {"decision": ASK, "to": "human", "timing": timing(HIGH), "reason": str(signal.get("reason") or ""), "severity": severity}
