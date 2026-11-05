"""The interface of RequestIntaking: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("request-intake", kind="event", entry="receive", example={"person": ""})
@runtime_checkable
class RequestIntaking(typing.Protocol):
    """Takes in the requests people make, from every source Body declares, each attached to the person who made it; nothing a person asked is
    lost or taken twice."""

    def receive(self, person: str = "", sources: Sequence[str] = ()) -> Sequence[Mapping[str, Any]]: ...
