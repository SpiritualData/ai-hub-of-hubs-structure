"""Relevant Solutions by the records' index, then a cheap model: the esoi library's lexical arm gives a wider list of candidate solutions
(three times the limit, so a solution a request names in other words still has a chance), and one cheap call through Model Plumbing picks among
them from each candidate's name and purpose. Each picked solution gets its chain of parents and its dependents from the records. Standard library
plus the hub and ``esoi``."""
from typing import Any, Mapping

from esoi import Lazy, implementation

from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import network_of
from hubofhubs.the_intelligence.subconscious.relevant_solutions.records_index import shaped
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing

CANDIDATES = "lexical_index"


@implementation("relevant-solutions", "records_then_model")
class RecordsThenModel:
    """The records index narrows to candidates, a cheap model call picks the solutions the request concerns among them."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "cheap"):
        self.plumbing, self.tier = plumbing, tier

    def relevant(self, request: str, records: Any, limit: int = 5, depth: int = 3) -> Mapping[str, Any]:
        from esoi.understanding.solution_relevance import relevance
        network = network_of(records)
        classify = relevance.model_arm(lambda prompt: self.plumbing.ask(prompt, self.tier), CANDIDATES)
        return shaped(network, classify(network.index, request, limit), depth)
