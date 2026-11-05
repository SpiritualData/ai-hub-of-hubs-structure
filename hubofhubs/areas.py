"""The composition arms of the areas that have callers: each takes the seats it uses as typed constructor parameters (the esoi
Assembler injects them) and offers the one operation a caller of the whole area wants.

``take-in-the-world`` (search and papers through the tools, the model through Model Plumbing, research freshness through Learning),
``model-plumbing`` (a model at a measured tier), ``stay-current`` (stale research) and ``keep-it-generic`` (an audit that reads Learning and
the share of connections that need no code, a metric of Tools). Standard library plus the hub and ``esoi``; nothing here reads the environment."""
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from . import registry, scan
from .measure import metrics as connection_metrics
from .oneline import hit_items
from .seats import FreshnessReading, ModelCall, ModelPlumbing, Staying, Tooling, TierSelection, WorldKnowing


@implementation("take-in-the-world", "composition")
class WorldComposition:
    """The outside world for a query: the answer and sources of Web Search, reached through Tools, and with ``scholarly=True`` the papers of
    Science as well (built on first use, so a plain search never asks for it). The same arm reaches the model through Model Plumbing (``ask``) and
    reports how current the hub's research is through Learning (``stale_areas``); both are built on first use."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, tools: Tooling, papers: Lazy[WorldKnowing], plumbing: Lazy[ModelPlumbing], learning: Lazy[Staying]):
        self.tools, self.papers, self.plumbing, self.learning = tools, papers, plumbing, learning

    def take_in(self, query: str, scholarly: bool = False) -> Mapping[str, Any]:
        response = self.tools.use("search-backend", query)
        items = hit_items(response.hits)
        answer = response.answer or "\n".join(f"{i.get('title', '')}: {i.get('snippet', '')}".strip(": ") for i in items)
        if scholarly:
            observation = self.papers.search(query, max_results=5)
            items += hit_items(getattr(observation, "hits", ()) or ())
        return {"answer": answer, "items": items}

    def ask(self, prompt: str, tier: str = "") -> str:
        return self.plumbing.ask(prompt, tier)

    def stale_areas(self, today: str = "") -> Sequence[str]:
        return self.learning.stale_areas(today)


@implementation("model-plumbing", "composition")
class ModelCalls:
    """A prompt asked of the model the tier chooser measured best for the tier; a name the chooser does not list is passed on as the model name
    itself. The chooser is built on first use, so a prompt with no tier never asks for it."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, model: ModelCall, chooser: Lazy[TierSelection]):
        self.model = model
        self.chooser = chooser

    def ask(self, prompt: str, tier: str = "") -> str:
        arm = (self.chooser.choose().get(tier) or {}).get("arm") if tier else None
        return self.model.complete(prompt, arm[1] if arm else tier)


@implementation("stay-current", "registry_research")
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


def config_share(area: str = "") -> float:
    """The share of an area's wired hub connections that need no code (the metric of Tools and of Hands; all areas when none is named)."""
    rows = [r for r in registry.read("hub_capabilities.csv") if r.get("wired", "yes") == "yes" and (not area or r["area"] == area)]
    return float(connection_metrics({}, rows)["config_share"])


@implementation("keep-it-generic", "prompts_as_data")
class PromptsAsData:
    """An audit of the hub for consumer wording: the vendor-name branches in its own code for the terms given, beside how stale its
    research is and how much of it connects by configuration."""
    REQUIRES = ()     # the seat it is handed

    def __init__(self, stay: Staying):
        self.stay = stay

    def audit(self, terms: Sequence[str]) -> Mapping[str, Any]:
        package = Path(__file__).resolve().parent
        branches = scan.scan_core({"hub": list(terms)}, package, package.parent)["hub"] if terms else []
        return {"vendor_branches": branches, "stale_areas": list(self.stay.stale_areas()), "config_share": config_share()}
