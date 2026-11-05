"""The one signal the Nervous System sends: a severity and a reason. Standard library only.

The Nervous System says how risky the next step is and why; it does not route. What to do with the signal belongs to the parts that own
it: Judgment Calls decides for the person whether to ask, proceed or decline (it owns asking), and the Planner and Delegation own the
routing that an overseer used to hint at (answer now, hand the work to an agent session, change course). ``to_risk_signal`` reads an
overseer's older five-way verdict into a severity so the engines that still speak it stay one signal at the seat."""
from dataclasses import dataclass
from typing import Any

NONE, LOW, MEDIUM, HIGH = "none", "low", "medium", "high"
SEVERITIES = (NONE, LOW, MEDIUM, HIGH)
RANK = {name: index for index, name in enumerate(SEVERITIES)}

# What an overseer's verdict meant for risk: a step to stop and hand to a person is high, a step to change is medium, work that only
# needs a different worker is low, and the rest carries none.
VERDICT_SEVERITY = {"proceed": NONE, "answer_now": NONE, "escalate_deep": LOW, "redirect": MEDIUM, "escalate_human": HIGH}


@dataclass(frozen=True)
class RiskSignal:
    """How risky the next step is (``severity``: none, low, medium or high) and why (``reason``, one user-safe sentence, empty for none).
    ``degraded`` is true when ``none`` is only what an engine fell back to after a failure, never a verdict."""
    severity: str = NONE
    reason: str = ""
    degraded: bool = False

    def at_least(self, severity: str) -> bool:
        return RANK[self.severity] >= RANK[severity]


def to_risk_signal(verdict: Any) -> RiskSignal:
    """The risk signal for an overseer verdict (an object with ``signal``, ``reason`` and ``degraded``)."""
    return RiskSignal(VERDICT_SEVERITY.get(getattr(verdict, "signal", NONE), NONE), getattr(verdict, "reason", "") or "",
                      bool(getattr(verdict, "degraded", False)))
