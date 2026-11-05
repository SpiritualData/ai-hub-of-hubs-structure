"""The interface of TierSelection: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("model-tier-chooser", kind="event", entry="choose", example={"available": ["anthropic"]})
@runtime_checkable
class TierSelection(typing.Protocol):
    """Per model tier, pick the (provider, model) arm with the most passing work per cost. ``choose`` reads the registry's own
    arms, prices and measurements and returns ``{tier: {arm, reason, scored}}``; ``select`` does the same for data you pass."""

    def choose(self, folder: Any = None, available: Optional[Sequence[str]] = None, credits: Optional[Sequence[Mapping[str, str]]] = None,
               **bars: Any) -> Mapping[str, Any]: ...

    def select(self, tiers: Mapping[str, Sequence[Mapping[str, Any]]], prices: Sequence[Mapping[str, str]],
               credits: Sequence[Mapping[str, str]] = (), defaults: Any = None, **bars: Any) -> Mapping[str, Any]: ...
