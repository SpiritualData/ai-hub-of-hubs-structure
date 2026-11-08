"""Relevant Solutions by the records' own index: the esoi library's classifier over the specification index (the records-selected arm,
lexical hits plus the records each hit links to), with each solution's chain of scopes above it and the solutions that rely on it. No model
call. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, List, Mapping

from esoi import implementation

from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import network_of


@implementation("relevant-solutions", "records_index")
class RecordsIndex:
    """The solutions a request concerns, found by the records' specification index, each with its chain of parents and its dependents."""
    REQUIRES = ()     # the records are an argument of the call

    def relevant(self, request: str, records: Any, limit: int = 5, depth: int = 3) -> Mapping[str, Any]:
        network = network_of(records)
        return shaped(network, network.classify(request, limit), depth)


def shaped(network: Any, hits: List[Mapping[str, Any]], depth: int) -> Mapping[str, Any]:
    """The arm's answer: each solution hit with its name, its chain of parents and its dependents."""
    found: List[Dict[str, Any]] = []
    for hit in hits:
        sid = hit["solution_id"]
        found.append({"solution_id": sid, "name": network.name(sid), "score": hit.get("score", 0.0), "via": list(hit.get("via") or []),
                      "chain": network.chain(sid, depth), "dependents": network.dependents(sid)})
    return {"solutions": found, "records": str(getattr(network, "root", ""))}
