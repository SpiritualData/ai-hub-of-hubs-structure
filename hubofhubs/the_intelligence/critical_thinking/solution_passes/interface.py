"""The interface of SolutionConsidering: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, runtime_checkable
from esoi import solution

#: The limits of one request's consideration. A relevant solution's own pass is never cut by them; only parent and dependent passes are.
DEFAULT_LIMITS = {"depth": 3, "calls": 40, "width": 8}


@solution("solution-passes", kind="event", entry="consider", example={"request": "should the selected arm change?", "briefs": {"solutions": []}})
@runtime_checkable
class SolutionConsidering(typing.Protocol):
    """Gives each solution a request concerns its own consideration: one pass per relevant solution, with that solution's generated prompt, says what the
    solution needs from the request, the target its own metric sets, the risks and any conflict with its recorded results; then a narrower pass per scope
    above, climbing one level at a time and stopping at the first scope whose pass finds no effect on how its children combine; and a narrow pass per
    dependent on whether what it relies on still holds.

    ``briefs`` is what the Subconscious prepared (``solutions``, ``ancestors``, ``dependents``, each with its ``prompt``). ``own_passes`` maps a solution
    id to the consumer's own pass for it (``(request, brief) -> finding``), used instead of a model pass. ``ask`` is a one-argument model call that
    replaces the arm's own. The result holds ``findings`` (one per relevant solution: ``solution_id``, ``applies``, ``needs``, ``target``
    (``metric_id``, ``value``, ``done_when``), ``risks``, ``conflicts``, ``knowledge``, ``candidates``), ``parents`` (``solution_id``, ``level``,
    ``children``, ``serves_purpose``, ``siblings_affected``, ``metric_update``, ``combination_effect``, ``why``), ``dependents`` (``solution_id``,
    ``relies_on``, ``still_holds``, ``why``), ``calls``, ``cut`` (passes left out by the limits, with why) and ``stopped_at``."""

    def consider(self, request: str, briefs: Mapping[str, Any], own_passes: Optional[Mapping[str, Callable[..., Mapping[str, Any]]]] = None,
                 limits: Optional[Mapping[str, int]] = None, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]: ...
