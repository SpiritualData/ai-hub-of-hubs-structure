"""The interface of ResponseJudging: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("response-quality", kind="event", entry="judge", example={"response": "See https://example.org/a for details.", "evidence": "https://example.org/a"})
@runtime_checkable
class ResponseJudging(typing.Protocol):
    """Judges a response against a quality profile (``QualityProfile``: named criteria with weights and targets; the default profile when none
    is given) and returns one finding per criterion the response does not meet, as strings. An empty list means the response held. Each arm
    judges one criterion (links held to the evidence, figures grounded in the evidence, no em dash, day counts that match the calendar);
    ``critique`` is that judgment alone, and ``repair`` returns the response with what fails that criterion taken out or rewritten by
    a fixed rule (the response as given when the criterion has no safe repair)."""

    def judge(self, response: str, evidence: str = "", profile: Optional[Any] = None) -> Sequence[str]: ...
    def critique(self, answer: str, evidence: str = "") -> Sequence[str]: ...
    def repair(self, response: str, evidence: str = "") -> str: ...
