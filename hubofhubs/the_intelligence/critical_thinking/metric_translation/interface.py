"""The interface of MetricTranslating: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("metric-translation", kind="event", entry="translate", example={"request": "what is the latest Rust version?"})
@runtime_checkable
class MetricTranslating(typing.Protocol):
    """Turns a request into a metric with a target value or improvement, adjustable in real time, applied to each sub-goal. Given ``solutions`` (the
    targets the relevant solutions' own passes read from their own metrics: ``solution_id``, ``metric_id``, ``value``, ``done_when``), the goal is held
    to those targets and no metric is invented."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None, solutions: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]: ...
