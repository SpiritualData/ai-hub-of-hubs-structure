"""The interface of TierSelection: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("model-tier-chooser", kind="event", entry="choose", example={"available": ["anthropic"]})
@runtime_checkable
class TierSelection(typing.Protocol):
    """Per model tier (fast, balanced, quality, best), pick the default arm from the tier's own metric over public evaluations (weights in
    ``tier_metrics.csv``, numbers in ``registry/tier_public_scores.csv``), with cost and speed as factors except for best; the hub's own measured
    work per cost overrides it only with at least 100 shared cases per arm. ``choose`` returns ``{tier: {arm, effort, reason, scored, stage}}`` with the
    score breakdown and the runner-up; ``available`` (or ``environ``, a mapping, never the process environment) limits the providers and ``role`` names
    a domain whose metric variant applies (for example ``science``). ``select`` ranks measured arms you pass by passing work per cost."""

    def choose(self, folder: Any = None, available: Optional[Sequence[str]] = None, credits: Optional[Sequence[Mapping[str, str]]] = None,
               today: str = "", role: str = "", environ: Optional[Mapping[str, str]] = None, **bars: Any) -> Mapping[str, Any]: ...

    def select(self, tiers: Mapping[str, Sequence[Mapping[str, Any]]], prices: Sequence[Mapping[str, str]],
               credits: Sequence[Mapping[str, str]] = (), defaults: Any = None, **bars: Any) -> Mapping[str, Any]: ...
