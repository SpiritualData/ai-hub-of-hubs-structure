"""The interface of EsoiApplying: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("esoi-application", kind="event", entry="apply", example={"change": {}})
@runtime_checkable
class EsoiApplying(typing.Protocol):
    """Applies a proposed change to the specs and metrics of the system as one field edit, or refuses it with the reason."""

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]: ...
