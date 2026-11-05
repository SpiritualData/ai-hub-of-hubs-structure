"""The interface of Delegating: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("delegation", kind="event", entry="delegate", example={"pieces": [], "authority": {}})
@runtime_checkable
class Delegating(typing.Protocol):
    """Hands each piece to the right worker, only when necessary, carrying the Representative's ``authority`` and the sub-goal's done-standard;
    returns one result per piece. It enforces three limits and owns the last: the authority (a worker category not allowed is refused), the
    goal record's ``budget`` (pieces and dollars) and cancellation (``cancelled`` is checked before each piece and reaches a running agent session
    through the worker's own stop hook). A piece it did not run comes back with ``refused`` and the reason."""

    def delegate(self, pieces: Sequence[Mapping[str, Any]], authority: Optional[Mapping[str, Any]] = None, budget: Optional[Mapping[str, Any]] = None,
                 cancelled: Optional[Callable[[], bool]] = None) -> Sequence[Mapping[str, Any]]: ...
