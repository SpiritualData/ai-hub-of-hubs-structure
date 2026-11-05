"""The interface of Prioritizing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("prioritization", kind="event", entry="prioritize", example={"person": "", "request": "what is the latest Rust version?"})
@runtime_checkable
class Prioritizing(typing.Protocol):
    """Translates the priorities a person states or implies into ESOI milestones and weights, and puts the work that competes for attention in order.
    Given ``candidates`` (mappings with ``id``, ``kind`` and the fields the consumer's data carries, see ``types.FIELDS``), what the person ``stated`` (an
    explicit order, what to defer, what their feedback implies, quality weights) and the time, it returns ``ordered`` (each item with its ``rank``, the
    ``reason`` in words and a ``metric`` that Metric Translation and the Planner use), ``held`` (items the person's constraints keep back, with why),
    ``quality_weights`` for the quality profile and ``constraints``. With no candidates it returns only the weights. It decides nothing about whether
    work may be done unasked, which belongs to Judgment Calls."""

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None, candidates: Sequence[Mapping[str, Any]] = (),
                   stated: Any = None, now: str = "") -> Mapping[str, Any]: ...
