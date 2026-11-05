"""The interface of ContextTaking: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("context-intake", kind="event", entry="take", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class ContextTaking(typing.Protocol):
    """The one intake of the Mind: takes what the Subconscious prepared and what the World brought and returns one view."""

    def take(self, request: str, prepared: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
