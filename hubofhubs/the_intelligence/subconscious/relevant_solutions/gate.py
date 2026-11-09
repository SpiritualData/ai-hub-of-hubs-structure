"""Which of the solutions Relevant Solutions returned are worth a model pass: those scoring at or above a threshold.

The records index scores every request against some solution, so a turn that is not about any of them still gets a ranked list; a pass on
such a list costs model calls for nothing. The default threshold was fixed from the hub's 62 relevance cases before any chat run was
measured, by one rule: the lowest records-index score at which a returned solution is gold at least half the time (73: precision 0.50,
55 of the 63 gold solutions kept, 58 of 62 cases with at least one solution kept). Scores are the records index's own units, so a consumer
whose records differ in size may fix its own threshold from its own cases by the same rule (``threshold_from_cases``). Standard library."""
from typing import Any, Iterable, List, Mapping, Sequence, Tuple

DEFAULT_MIN_SCORE = 73.0


def selected(found: Sequence[Mapping[str, Any]], min_score: float = DEFAULT_MIN_SCORE) -> List[Mapping[str, Any]]:
    """The solutions scoring at or above ``min_score``, best first (none means the request concerns no solution enough for a pass)."""
    return [f for f in found if float(f.get("score") or 0.0) >= min_score]


def threshold_from_cases(scored: Iterable[Tuple[float, bool]], precision: float = 0.5) -> float:
    """The rule the default came from: the lowest score at which returned solutions (``(score, was it gold)``) are gold at least
    ``precision`` of the time; infinity when no score reaches it."""
    points = list(scored)
    for cut in sorted({round(s) for s, _ in points}):
        kept = [gold for s, gold in points if s >= cut]
        if kept and sum(kept) / len(kept) >= precision:
            return float(cut)
    return float("inf")
