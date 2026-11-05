"""The interface of Representing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("the-representatives", kind="event", entry="represent", example="")
@runtime_checkable
class Representing(typing.Protocol):
    """The AI persona that acts for a person: returns the person's authority, preferences and quality profile."""

    def represent(self, person: str = "") -> Mapping[str, Any]: ...
