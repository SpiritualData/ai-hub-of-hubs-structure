"""The interface of TakingIn: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("the-world", kind="event", entry="take_in", example="latest Rust release")
@runtime_checkable
class TakingIn(typing.Protocol):
    """Brings the outside world in for a query: a web search, and with ``scholarly=True`` the papers of the world-knowing seat too.
    Returns ``{"answer": text, "items": [hits with their sources]}``. ``stale_areas`` names the areas of the hub's research that are out of date
    (Learning's reading), which The Self reports in its health."""

    def take_in(self, query: str, scholarly: bool = False) -> Mapping[str, Any]: ...
    def stale_areas(self, today: str = "") -> Sequence[str]: ...
