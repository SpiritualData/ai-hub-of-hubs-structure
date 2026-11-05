"""The interface of EsoiApplying: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("esoi-application", kind="event", entry="apply", example={"change": {}})
@runtime_checkable
class EsoiApplying(typing.Protocol):
    """Creates and edits specs and metrics from a proposed change and runs the iterative improvement loop."""

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]: ...
