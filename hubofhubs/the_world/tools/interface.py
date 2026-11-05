"""The interface of Tooling: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("the-tools", kind="event", entry="use", example={"category": "web-search", "request": "latest Rust release"})
@runtime_checkable
class Tooling(typing.Protocol):
    """Uses the tool of one category (``web-search``, ``read-files``, ``file-editing``, ``connected-system-operations`` or
    ``delegated-agent-sessions``) by calling that category's entry point with the request. A category the Representative's authority does not
    allow is refused by Delegation, and a request that names the ``owner`` of the data it reads (a person) outside the ``data_scope`` of the
    ``authority`` it is given is refused here: data scope is enforced by Tools and by Body's adapters, which declare whose each source is."""

    def use(self, category: str, request: Any, cancel_check: Optional[Callable[[], bool]] = None, authority: Optional[Mapping[str, Any]] = None) -> Any: ...
