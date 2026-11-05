"""WorldComposition."""
from typing import Any, Mapping, Sequence
from esoi import implementation
from esoi.assemble import Lazy
from hubofhubs.the_self.assembler.oneline import hit_items
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing
from hubofhubs.the_world.learning.interface import Staying
from hubofhubs.the_world.tools.interface import Tooling
from hubofhubs.the_world.science.interface import WorldKnowing


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
