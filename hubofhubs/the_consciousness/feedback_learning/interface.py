"""The interface of FeedbackLearning: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("feedback-learning", kind="event", entry="learn", example={"person": "", "feedback": {}})
@runtime_checkable
class FeedbackLearning(typing.Protocol):
    """Turns a person's feedback into proposed edits to specs and metrics (never to prompts), including quality profile changes, for ESOI
    Application to apply."""

    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
