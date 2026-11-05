"""The one signal the Nervous System sends: a severity and a reason. Standard library only.

The Nervous System says how risky the next step is and why; it does not route. What to do with the signal belongs to the parts that own
it: Judgment Calls decides for the person whether to ask, proceed or decline (it owns asking), and Planner and Delegation own the routing that
an overseer used to hint at (answer now, hand the work to an agent session, change course). A step the rules cannot classify is ``medium``,
never ``none``: an unchecked step is not a safe one."""
from dataclasses import dataclass

NONE, LOW, MEDIUM, HIGH = "none", "low", "medium", "high"
SEVERITIES = (NONE, LOW, MEDIUM, HIGH)
RANK = {name: index for index, name in enumerate(SEVERITIES)}

@dataclass(frozen=True)
class RiskSignal:
    """How risky the next step is (``severity``: none, low, medium or high) and why (``reason``, one user-safe sentence, empty for none).
    ``degraded`` is true when ``none`` is only what an engine fell back to after a failure, never a verdict."""
    severity: str = NONE
    reason: str = ""
    degraded: bool = False

    def at_least(self, severity: str) -> bool:
        return RANK[self.severity] >= RANK[severity]
