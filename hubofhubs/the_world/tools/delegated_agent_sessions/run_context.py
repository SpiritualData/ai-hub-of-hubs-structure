"""What a run is told besides the goal text it is started with, handed to the runner explicitly (never a module-level variable).

Role: a wrapper around a session harness (the configured-context ``Grounded``) adds text after the person's goal, so the goal a runner receives is no longer the person's own words,
and a helper the main session starts sees none of that text. The wrapper therefore gives the runner a ``RunContext`` before the run: ``original`` (the person's first message,
verbatim, which the answer check, the stop decision and the helper brief read) and ``notes`` (the saved-notes block the wrapper selected, which the helper brief carries). ``attach``
walks from a harness down through its wrappers (``.harness``) to the runner (``.runner``) and sets ``run_context`` on it; a runner reads ``run_context`` when a run starts. Pure
code, standard library only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunContext:
    """``original``: the person's first message of the session, verbatim ("" on a resumed turn: the runner keeps the first one). ``notes``: the saved-notes block the helpers carry ("" when none)."""
    original: str = ""
    notes: str = ""


def runner_of(harness: Any, depth: int = 8) -> Any:
    """The runner under ``harness`` (the first object on the chain ``.harness``, ``.runner`` that takes a run context), or None."""
    node = harness
    for _ in range(depth):
        if node is None:
            return None
        found = node.__dict__.get("runner") if hasattr(node, "__dict__") else None
        if found is not None and hasattr(found, "run_goal"):
            return found
        node = node.__dict__.get("harness") if hasattr(node, "__dict__") else None
    return None


def attach(harness: Any, context: RunContext) -> bool:
    """Give the runner under ``harness`` the context of the run about to start; False when there is no runner to give it to (the run then reads the goal it is started with)."""
    runner = runner_of(harness)
    if runner is None:
        return False
    try:
        runner.run_context = context
    except AttributeError:
        return False
    return True


__all__ = ["RunContext", "attach", "runner_of"]
