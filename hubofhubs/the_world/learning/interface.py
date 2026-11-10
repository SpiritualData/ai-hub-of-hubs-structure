"""The interface of Staying: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("the-learning", kind="event", entry="stale_areas", example="2026-11-03")
@runtime_checkable
class Staying(typing.Protocol):
    """Keeps what the hub knows current, by doing every knowledge search as a small systematic review. ``stale_areas`` names the areas of the registry whose
    research is older than the ninety day bar on a given date (ISO, default today). ``review`` takes a research question and the decision it informs, sizes the
    review by the decision's ``weight`` (quick, standard or full), fixes the method before searching, searches through Web Search and The Science, screens with a
    count for each reason, extracts and grades each kept item, synthesises what is known, contested and unknown, decides for each candidate, states what each item
    changed and when to revisit, and returns the record of the ESOI research standard (``research``, ``items``, ``applied``, ``protocol``, ``queries``,
    ``screened_out``, ``gaps``). ``due_reviews`` returns what learning is due: reviews past their revisit date, experiments past their reevaluation date and
    registry areas stale or never reviewed, each with the ``request`` to run, the most overdue first. ``standing_schedule`` is the weekly refresh as a schedule that
    Proactivity reads."""

    def stale_areas(self, today: str = "") -> Sequence[str]: ...

    def review(self, question: str, decision: str, weight: Any = None, size: str = "", links: Sequence[str] = (), criteria: Optional[Mapping[str, Any]] = None,
               candidates: Sequence[str] = (), queries: Sequence[str] = (), intent_id: str = "", experiment_id: str = "", today: str = "",
               refresh_days: Optional[int] = None, research_id: str = "", use_model: bool = False) -> Mapping[str, Any]: ...

    def due_reviews(self, today: str = "", root: Any = None) -> Sequence[Mapping[str, Any]]: ...

    def standing_schedule(self, last_run: str = "") -> Mapping[str, Any]: ...
