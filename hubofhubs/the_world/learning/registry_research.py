"""RegistryResearch: the baseline Learning arm. It reads the registry's dates and, asked for a review, runs one search through The Science and lists the hits
as they came: no protocol, no screening, no counts, no grades, no decisions. It is what a review without the standard looks like, and the bar
``systematic_review`` has to beat."""
from datetime import date
from typing import Any, Mapping, Optional, Sequence
from esoi import Lazy, implementation
from hubofhubs.the_world.learning import research_review as rr, review_store
from hubofhubs.the_world.learning.research_freshness_reader.interface import FreshnessReading
from hubofhubs.the_world.science.interface import WorldKnowing


@implementation("the-learning", "registry_research")
class RegistryResearch:
    """The areas whose last research is older than the registry's ninety day bar, read through the freshness seat; a review is one search and its hits."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, freshness: FreshnessReading, science: Lazy[WorldKnowing]):
        self.freshness, self.science = freshness, science

    def stale_areas(self, today: str = "") -> Sequence[str]:
        return review_store.stale_areas(self.freshness, today)

    def due_reviews(self, today: str = "", root: Any = None) -> Sequence[Mapping[str, Any]]:
        return review_store.due(today, root, self.freshness)

    def standing_schedule(self, last_run: str = "") -> Mapping[str, Any]:
        return review_store.standing_schedule(last_run)

    def review(self, question: str, decision: str, weight: Any = None, size: str = "", links: Sequence[str] = (), criteria: Optional[Mapping[str, Any]] = None,
               candidates: Sequence[str] = (), queries: Sequence[str] = (), intent_id: str = "", experiment_id: str = "", today: str = "",
               refresh_days: Optional[int] = None, research_id: str = "", use_model: bool = False) -> Mapping[str, Any]:
        day = today or date.today().isoformat()
        found = list(self.science.search(question).hits)
        row = {c: "" for c in rr.COLUMNS}
        row.update(research_id=research_id or "r-naive", kind="review", intent_id=intent_id, question=question, decision=decision, done_on=day, found=str(len(found)),
                   kept=str(len(found)))
        items = [{"research_id": row["research_id"], "item_id": f"i{n}", "claim": str(h.get("title", "")) if isinstance(h, Mapping) else str(h)} for n, h in enumerate(found, 1)]
        return {"research": row, "items": items, "applied": [], "protocol": {}, "queries": [{"source": "scholarly search", "query": question, "date": day, "hits": len(found)}],
                "screened_out": {}, "gaps": rr.gaps(row, items)}
