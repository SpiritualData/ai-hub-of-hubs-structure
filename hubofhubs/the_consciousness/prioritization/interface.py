"""The interface of Prioritizing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("prioritization", kind="event", entry="prioritize", example={"person": "", "request": "what is the latest Rust version?"})
@runtime_checkable
class Prioritizing(typing.Protocol):
    """The one solution that orders, for a person, the three things that compete for their attention, named by ``subject``: ``work`` (what the AI is about to
    start unasked; Proactivity asks for it), ``asks`` (the questions, decisions and approvals the AI puts to the person, which Judgment Calls decided to make and
    asks Prioritization to order and batch) and ``goals`` (the person's own goals, which in the hub are solution milestones as the ESOI specification defines them; Objectives asks which matter most). Given ``candidates`` (mappings with ``id``,
    ``kind`` and the fields the consumer's data carries, see ``types.FIELDS``: for an ask what it ``unblocks``, its ``effort``, ``deadline`` and when the person
    was last asked; for a milestone its ``solution``, ``intent``, target ``deadline``, what it is ``blocked_by`` and ``unblocks``, whether it is ``met``), what the person ``stated`` (an explicit order, what to defer, what their feedback
    implies, quality weights) and the time, it returns ``ordered`` (each item with its ``rank``, the ``reason`` in words and a ``metric`` that Metric Translation
    and the Planner use), ``held`` (items the person's constraints keep back, and with a ``batch_limit`` above zero the asks beyond the batch, each with its place
    and why), ``subject``, ``quality_weights`` for the quality profile and ``constraints``. ``batch_limit`` is how many items to put in front of the person at once
    (zero is no limit). With no candidates it returns only the weights. It decides nothing about whether work may be done unasked or whether to ask, which belong
    to Judgment Calls, and holds no goals, which Objectives does."""

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None, candidates: Sequence[Mapping[str, Any]] = (),
                   stated: Any = None, now: str = "", subject: str = "work", batch_limit: int = 0) -> Mapping[str, Any]: ...
