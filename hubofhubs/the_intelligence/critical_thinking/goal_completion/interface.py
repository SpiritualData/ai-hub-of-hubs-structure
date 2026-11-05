"""The interface of GoalCompleting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("goal-completion", kind="event", entry="check", example={"goal": "answer the question", "done_standard": "a cited answer", "outcome": ""})
@runtime_checkable
class GoalCompleting(typing.Protocol):
    """Says whether a goal's condition was met against its done-standard: a mapping with ``met`` and ``reason``."""

    def check(self, goal: str, done_standard: str, outcome: Any) -> Mapping[str, Any]: ...
