"""The interface of Staying: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Sequence, runtime_checkable
from esoi import solution


@solution("the-learning", kind="event", entry="stale_areas", example="2026-11-03")
@runtime_checkable
class Staying(typing.Protocol):
    """Names the areas of the registry whose research is older than the ninety day bar on a given date (ISO, default today)."""

    def stale_areas(self, today: str = "") -> Sequence[str]: ...
