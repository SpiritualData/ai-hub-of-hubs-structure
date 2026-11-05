"""The interface of HumanAdapting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("the-consciousness", kind="event", entry="represent", example="")
@runtime_checkable
class HumanAdapting(typing.Protocol):
    """Adapts the system to a person: ``represent`` returns the person's Representative (authority, preferences, quality profile and
    priorities), ``receive`` takes in the requests people made, ``learn`` applies the person's feedback to specs and metrics."""

    def represent(self, person: str = "") -> Mapping[str, Any]: ...
    def receive(self, person: str = "") -> Sequence[Mapping[str, Any]]: ...
    def learn(self, person: str = "", feedback: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
