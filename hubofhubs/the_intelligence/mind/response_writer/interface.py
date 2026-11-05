"""The interface of ResponseWriting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("response-writer", kind="event", entry="write", example={"results": [], "profile": None})
@runtime_checkable
class ResponseWriting(typing.Protocol):
    """Writes the plan, request or communication the Mind outputs for its reader, to the quality profile that applies."""

    def write(self, results: Sequence[Mapping[str, Any]], profile: Optional[Any] = None) -> str: ...
