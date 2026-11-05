"""The interface of RoleUnderstanding: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("role-understanding", kind="event", entry="state_role", example="the-assembler")
@runtime_checkable
class RoleUnderstanding(typing.Protocol):
    """States the role of a part (what it is responsible for, what it is not, who owns that) from its record, so a part and the Assembler can both
    read it. The result names the part, says whether any record states it (``stated``), and carries ``purpose``, ``out_of_scope`` and ``delegates_to``
    (the ids of the owners); an arm that checks the role also lists ``contradictions``, each a ``code`` and a ``detail``."""

    def state_role(self, part_id: str) -> Mapping[str, Any]: ...
