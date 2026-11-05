"""The interface of WholeAssembling: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("the-assembler", kind="event", entry="coverage", example={})
@runtime_checkable
class WholeAssembling(typing.Protocol):
    """Builds the whole from the best-measured arm of every seat and reports its coverage: which seats are built and, for each that is not, what
    exactly to pass or set. It runs nothing for a request; the flow of a request is The Self's."""

    def coverage(self, environ: Optional[Mapping[str, str]] = None) -> Mapping[str, Any]: ...
