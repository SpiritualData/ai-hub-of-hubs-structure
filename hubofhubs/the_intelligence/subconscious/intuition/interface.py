"""The interface of Intuiting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("the-intuition", kind="event", entry="offer", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class Intuiting(typing.Protocol):
    """What surfaces for a request unasked: the items closest to it, within a limit, for the Mind to take or ignore."""

    def offer(self, request: str, limit: int = 5) -> Sequence[Mapping[str, Any]]: ...
