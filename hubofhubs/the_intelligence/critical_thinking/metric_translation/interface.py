"""The interface of MetricTranslating: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("metric-translation", kind="event", entry="translate", example={"request": "what is the latest Rust release?"})
@runtime_checkable
class MetricTranslating(typing.Protocol):
    """Turns a request into a metric with a target value or improvement, adjustable in real time, applied to each sub-goal."""

    def translate(self, request: str, parent: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
