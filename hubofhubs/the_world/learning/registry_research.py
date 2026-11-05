"""RegistryResearch."""
from datetime import date
from typing import Sequence
from esoi import implementation
from hubofhubs.the_world.learning.research_freshness_reader import registry
from hubofhubs.the_world.learning.research_freshness_reader.interface import FreshnessReading


@implementation("the-learning", "registry_research")
class RegistryResearch:
    """The areas whose last research is older than the registry's ninety day bar, read through the freshness seat."""
    REQUIRES = ()     # the seat it is handed

    def __init__(self, freshness: FreshnessReading):
        self.freshness = freshness

    def stale_areas(self, today: str = "") -> Sequence[str]:
        day = date.fromisoformat(today) if today else None
        stale = []
        for row in registry.read("hubs.csv"):
            age = self.freshness.days_since(row["last_researched"], day)
            if age is None or age > registry.STALENESS_DAYS:
                stale.append(row["area"])
        return stale
