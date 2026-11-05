"""The interface of Objectives: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("live-objectives", kind="event", entry="current", example="")
@runtime_checkable
class Objectives(typing.Protocol):
    """The live hierarchy of intents and goals across requests: ``current`` returns it, ``place`` puts a request under the objective it serves."""

    def current(self, person: str = "") -> Sequence[Mapping[str, Any]]: ...
    def place(self, request: str, person: str = "") -> Mapping[str, Any]: ...
