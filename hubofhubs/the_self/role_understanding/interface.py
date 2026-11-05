"""The interface of RoleUnderstanding: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("role-understanding", kind="event", entry="state_role", example="the-assembler")
@runtime_checkable
class RoleUnderstanding(typing.Protocol):
    """A seat defined and empty: states the role of a part (what it is responsible for, what it is not, who owns that) from its record, so a
    part and the Assembler can both read it."""

    def state_role(self, part_id: str) -> Mapping[str, Any]: ...
