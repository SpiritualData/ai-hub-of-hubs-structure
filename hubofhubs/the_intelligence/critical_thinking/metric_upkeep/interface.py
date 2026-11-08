"""The interface of MetricUpkeeping: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, List, Mapping, Optional, runtime_checkable
from esoi import solution

#: The states a metric record can be in, decided by code from its fields.
STATES = ("fresh", "stale", "unmeasured", "no_source")
#: What upkeep does about a state.
ACTIONS = ("none", "read", "propose_source", "define_intermediate")


@solution("metric-upkeep", kind="event", entry="upkeep", example={"spec": {"solution_id": "s1", "moved_by": "ai"}, "metrics": {}})
@runtime_checkable
class MetricUpkeeping(typing.Protocol):
    """Keeps a milestone's metrics able to show progress: says by code whether each metric is fresh, stale, unmeasured or without a source, reads the stale
    ones it has a reader for, and when the milestone's own metric moves only through a person adds one intermediate metric the AI can move, after an
    independent check agrees it tracks the parent's done test.

    ``spec`` is the milestone (``solution_id``, ``name``, ``done_when``, ``moved_by``: ``person`` when its metric moves only through a person's act, else
    ``ai``). ``metrics`` maps metric record id to its fields (``record``, ``source``, ``measured_through``, ``expiration``, ``solution_ids``,
    ``parent_metric_ids``). ``readers`` maps a source name to a callable returning ``{"value", "as_of", "source"}``. ``today`` is an ISO date. ``ask`` is the
    one-argument model call for the proposal and the check. The result is one ``MetricAction`` per metric of the milestone: ``metric_id``, ``state``,
    ``action``, and, where they apply, ``reading``, ``proposed_source``, ``child_metric`` (with ``created``) and ``why``."""

    def upkeep(self, spec: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], readers: Optional[Mapping[str, Callable[[str], Mapping[str, Any]]]] = None,
               today: str = "", ask: Optional[Callable[[str], str]] = None) -> List[Mapping[str, Any]]: ...
