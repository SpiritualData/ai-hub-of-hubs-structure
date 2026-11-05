"""The composition arms of the areas that have callers: each takes the seats it uses as typed constructor parameters (the esoi
Assembler injects them) and offers the one operation a caller of the whole area wants.

``the-world`` (search and papers through the tools, the model through Model Plumbing, research freshness through Learning),
``model-plumbing`` (a model at a measured tier), ``the-learning`` (stale research) and ``system-integrity`` (an audit that reads Learning and
the share of connections that need no code, a metric of Tools). Standard library plus the hub and ``esoi``; nothing here reads the environment."""
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from . import registry, scan
from .measure import metrics as connection_metrics
from .oneline import hit_items
from .seats import FreshnessReading, ModelPlumbing, Staying, Tooling, TierSelection, WorldKnowing


@implementation("the-world", "composition")
class WorldComposition:
    """The outside world for a query: the answer and sources of Web Search, reached through Tools, and with ``scholarly=True`` the papers of
    Science as well (built on first use, so a plain search never asks for it). The same arm reaches the model through Model Plumbing (``ask``) and
    reports how current the hub's research is through Learning (``stale_areas``); both are built on first use."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, tools: Tooling, papers: Lazy[WorldKnowing], plumbing: Lazy[ModelPlumbing], learning: Lazy[Staying]):
        self.tools, self.papers, self.plumbing, self.learning = tools, papers, plumbing, learning

    def take_in(self, query: str, scholarly: bool = False) -> Mapping[str, Any]:
        response = self.tools.use("web-search", query)
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


def config_share(area: str = "") -> float:
    """The share of an area's wired hub connections that need no code (the metric of Tools and of Hands; all areas when none is named)."""
    rows = [r for r in registry.read("hub_capabilities.csv") if r.get("wired", "yes") == "yes" and (not area or r["area"] == area)]
    return float(connection_metrics({}, rows)["config_share"])


@implementation("system-integrity", "prompts_as_data")
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

    def audit_run(self, run: Mapping[str, Any]) -> Sequence[str]:
        """What the run says about itself, checked against what it did (a finding per claim the record does not support): every step names a
        status, a pending or skipped step says why, and an answer exists only when the Response Writer ran. Integrity audits what the system says
        about itself and what it did; Response Quality judges answers to people."""
        found: List[str] = []

        def walk(rows: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
            flat: List[Mapping[str, Any]] = []
            for row in rows:
                flat.append(row)
                flat += walk(row.get("steps") or ())
            return flat

        every = walk(run.get("steps") or ())
        for row in every:
            if row.get("status") not in ("done", "pending", "skipped"):
                found.append(f"step {row.get('solution', '?')} has no status")
            elif row["status"] != "done" and not row.get("reason"):
                found.append(f"step {row.get('solution', '?')} is {row['status']} and does not say why")
        if run.get("answer") and not any(r.get("solution") == "response-writer" and r.get("status") == "done" for r in every):
            found.append("an answer was given but the Response Writer did not run")
        return found
