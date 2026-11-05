"""The turn as a chain of phases that share one run-local namespace."""
from __future__ import annotations

from typing import Any, Callable, Optional, Sequence


def run_phases(state: Any, phases: Sequence[Callable[[Any], Optional[Any]]]) -> Optional[Any]:
    """Call each phase with ``state`` in order and return the first result that is not ``None``.

    A phase returns a terminal result to end the turn early, or ``None`` to go on. The last phase is expected to return the
    turn's result; if every phase returns ``None`` the result is ``None``. The phases are callables looked up by the caller at
    call time, so a host can replace one (a test, a replay) and the chain honours it.
    """
    for phase in phases:
        result = phase(state)
        if result is not None:
            return result
    return None
