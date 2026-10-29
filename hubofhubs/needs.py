"""Needs come from typed constructor parameters: a parameter annotated with a seat Protocol is a need of that seat."""
import inspect
import typing
from typing import Any, Dict, Optional

from esoi import runtime

from .resolution import SCOPE, HubError, prepare


def seat_of(protocol: Any) -> Optional[str]:
    """The solution id a seat Protocol was declared for, or None."""
    prepare()
    for (scope, sid), entry in runtime.REGISTRY.items():
        if scope == SCOPE and entry.interface is protocol:
            return sid
    return None


def protocol_of(solution_id: str) -> Any:
    entry = runtime.entry_of(solution_id, SCOPE)
    return entry.interface if entry is not None else None


def builder_of(target: Any) -> Any:
    """The callable that builds an arm: a class's ``__init__``, or the function itself."""
    if inspect.isclass(target):
        return None if target.__init__ is object.__init__ else target.__init__
    return target if inspect.isfunction(target) else None


def needs_of(target: Any) -> Dict[str, str]:
    """``{parameter name: solution id}`` for each parameter typed with a seat Protocol. An instance has none."""
    build = builder_of(target)
    if build is None:
        return {}
    try:
        hints = typing.get_type_hints(build)
    except Exception as error:   # a forward reference that does not resolve is a declaration bug: say so
        raise HubError(f"cannot read the parameter types of {getattr(target, '__qualname__', target)!r}: {error}") from error
    found = {}
    for param in inspect.signature(build).parameters:
        seat = seat_of(hints.get(param)) if param in hints else None
        if seat:
            found[param] = seat
    return found
