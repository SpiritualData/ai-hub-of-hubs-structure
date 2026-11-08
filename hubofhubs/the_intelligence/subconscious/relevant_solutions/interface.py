"""The interface of SolutionRelevance: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("relevant-solutions", kind="event", entry="relevant", example={"request": "should the selected arm change?", "records": "."})
@runtime_checkable
class SolutionRelevance(typing.Protocol):
    """Says which of a consumer's ESOI solutions a request concerns, so each one gets its own consideration. ``records`` is where the consumer's
    records are (a records root the esoi library can read, or an object with the same methods as ``network.SolutionNetwork``). The result maps
    ``solutions`` to a list, best first, of ``{solution_id, name, score, via, chain, dependents}``: ``via`` the records that reached it, ``chain``
    the parent ids from the nearest up to ``depth`` levels, and ``dependents`` ``{solution id: what it relies on}``; ``records`` names the root read."""

    def relevant(self, request: str, records: Any, limit: int = 5, depth: int = 3) -> Mapping[str, Any]: ...
