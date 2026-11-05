"""The interface of ContextTaking: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("context-intake", kind="event", entry="take", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class ContextTaking(typing.Protocol):
    """The one intake of the Mind: takes what the Subconscious prepared, what the World brought and the instructions that apply to the request (rules chosen for
    the request within a token budget, whose size is counted) and returns one view, with which instructions went in and how many tokens they cost."""

    def take(self, request: str, prepared: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None,
             instructions: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
