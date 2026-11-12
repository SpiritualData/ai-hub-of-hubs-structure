"""The interface of Representing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("the-representatives", kind="event", entry="represent", example="")
@runtime_checkable
class Representing(typing.Protocol):
    """One AI representative, whether it stands for a person or is a character with no person behind it: returns its identity, authority (worker categories, data scope never wider than what the asker may open, asking policy), preferences and quality profile."""

    def represent(self, representative: str = "", person: str = "") -> Mapping[str, Any]: ...
