"""The interface of GoalCompleting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("goal-completion", kind="event", entry="check", example={"goal": "answer the question", "done_standard": "a cited answer", "outcome": ""})
@runtime_checkable
class GoalCompleting(typing.Protocol):
    """Says whether a goal's condition was met against its done-standard: a mapping with ``met`` and ``reason``. Beside the verdict it says whether
    iteration the person did not ask for should go on (``decide_stop``): given an iteration history (see ``stop_rule``) it returns ``decision`` (one of
    ``continue``, ``stop_met``, ``stop_good_enough``, ``stop_not_worth_it``, ``ask``), ``continue`` (a bool), ``code``, ``reason``, ``facts`` and, for a stop that
    leaves work, ``left``. The person's stated limits and the policy and authority that bound the work are plain inputs of the history, resolved from
    Consciousness by the caller."""

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]: ...

    def decide_stop(self, history: Mapping[str, Any]) -> Mapping[str, Any]: ...
