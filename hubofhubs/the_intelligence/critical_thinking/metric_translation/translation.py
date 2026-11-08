"""Metric Translation: turns a request into the metric its goal is measured by, with a target value and the budget on the goal record.

The goal record is what the whole flow reads: ``metric`` (what is measured), ``target`` (the value or improvement that counts as met),
``done_standard`` (the words the Goal Completion check holds the outcome to), ``budget`` (attempts, pieces and dollars; owned here,
enforced by Delegation and Model Plumbing) and ``parent`` (the objective it rolls up to). A child goal never gets more budget than its parent
has left, and can be adjusted in real time by passing a new target. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, Mapping, Optional, Sequence

from esoi import implementation

DEFAULT_BUDGET = {"attempts": 3, "pieces": 8, "usd": None}


def child_budget(parent: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    left = dict((parent or {}).get("budget") or {})
    return {key: (min(value, left[key]) if left.get(key) is not None and value is not None else (left.get(key) if left.get(key) is not None else value))
            for key, value in DEFAULT_BUDGET.items()}


@implementation("metric-translation", "goal_record")
class GoalRecord:
    """A request becomes a goal record: it is met when the response addresses the request, within the default budget or what its parent has left. When
    the relevant solutions' own targets are given, the goal is met when each of them is, and its done-standard names each one."""
    REQUIRES = ()     # rules only

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None, solutions: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]:
        goal = " ".join(request.split())
        own = [s for s in solutions if s.get("done_when") or s.get("metric_id")]
        if own:
            standard = "; ".join(f"{s.get('name') or s.get('solution_id')}: {s.get('done_when') or 'its metric moves'}"
                                 + (f" ({s['metric_id']}{' ' + str(s['value']) if s.get('value') else ''})" if s.get("metric_id") else "") for s in own)
            return {"metric": "each relevant solution's own metric", "target": 1.0, "done_standard": standard, "budget": child_budget(parent),
                    "parent": (parent or {}).get("id", ""), "request": goal, "solutions": [dict(s) for s in own]}
        return {"metric": "goal met", "target": 1.0, "done_standard": f"a response that addresses: {goal}", "budget": child_budget(parent),
                "parent": (parent or {}).get("id", ""), "request": goal}
