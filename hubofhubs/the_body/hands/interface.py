"""The interface of Connecting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("the-hands", kind="event", entry="integrations", example="")
@runtime_checkable
class Connecting(typing.Protocol):
    """Hands: lists a system's enduring integrations (its AI tool registry, LLM platform, guardrails) and says
    which are accessible to the AI and which are used."""

    def integrations(self, system: str = "") -> Sequence[Mapping[str, Any]]: ...
