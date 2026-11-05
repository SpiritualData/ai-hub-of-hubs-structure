"""The interface of Genericity: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("system-integrity", kind="event", entry="audit", example=["examplevendor"])
@runtime_checkable
class Genericity(typing.Protocol):
    """Audits the hub for consumer wording: the vendor-name branches in its own code for the terms you give, with how stale its
    research is and how much of it connects by configuration."""

    def audit(self, terms: Sequence[str]) -> Mapping[str, Any]: ...
    def audit_run(self, run: Mapping[str, Any]) -> Sequence[str]: ...
