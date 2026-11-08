"""What the Subconscious prepares for each solution a request concerns: the solution's generated prompt (its stable part, from its network of
records) with only the knowledge that bears on this request, and the same for each scope above it and, narrower, for each solution that
relies on it. The prompts are never written by hand: the records form them. Knowledge items become cards in the kept cards (the managed
solution card and one card per item, retired items quarantined), and the selected Context Retriever picks among them per solution.

``knowledge`` says how items reach a prompt: ``retrieved`` (the default: what bears on the request), ``all`` (every active item) or ``none``.
Standard library plus the hub."""
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_intelligence.subconscious.cards_from_files.knowledge_cards import active, cards_of
from hubofhubs.the_intelligence.subconscious.context_retriever.knowledge_pick import pick, section

RETRIEVED, ALL, NONE = "retrieved", "all", "none"
DEPENDENT_BUDGET = 4000     # characters: a dependent's pass asks one narrow question


def brief_of(network: Any, sid: str, request: str, role: str, knowledge: str, retriever: Optional[Any], offered: Sequence[str],
             keep: Optional[Callable[[Sequence[Any]], Any]], budget: int = 0) -> Dict[str, Any]:
    made = network.prompt(sid, request, role, budget)
    cards = cards_of(sid, made)
    if keep is not None:
        keep(cards)
    items = active(cards)
    chosen = [] if knowledge == NONE else (items if knowledge == ALL else pick(request, items, retriever, offered, solution_name=network.name(sid)))
    extra = section(chosen)
    return {"solution_id": sid, "name": network.name(sid), "role": role, "prompt": made["text"] + (("\n\n" + extra) if extra else ""),
            "digest": made.get("digest", ""), "knowledge_total": len(items), "knowledge_picked": [c.id for c in chosen],
            "omitted": list(made.get("omitted") or [])}


def briefs(network: Any, found: Sequence[Mapping[str, Any]], request: str, knowledge: str = RETRIEVED, retriever: Optional[Any] = None,
           offered: Sequence[str] = (), keep: Optional[Callable[[Sequence[Any]], Any]] = None) -> Dict[str, Any]:
    """``solutions`` (each relevant solution with its ``prompt``), ``ancestors`` (one brief per scope above any of them, by id) and
    ``dependents`` (one narrow brief per solution relying on any of them, with ``relies``: what it relies on, by the solution it relies on)."""
    solutions: List[Dict[str, Any]] = []
    ancestors: Dict[str, Dict[str, Any]] = {}
    dependents: Dict[str, Dict[str, Any]] = {}
    relevant = {f["solution_id"] for f in found}
    for item in found:
        sid = item["solution_id"]
        solutions.append({**item, **brief_of(network, sid, request, "solution", knowledge, retriever, offered, keep)})
        for parent in item.get("chain") or ():
            if parent not in ancestors and parent not in relevant:
                ancestors[parent] = {**brief_of(network, parent, request, "parent", knowledge, retriever, offered, keep),
                                     "parent": network.parent(parent), "children": network.children(parent)}
        for other, how in (item.get("dependents") or {}).items():
            if other in relevant or other in ancestors:
                continue
            entry = dependents.setdefault(other, {**brief_of(network, other, request, "dependent", NONE, None, (), None, DEPENDENT_BUDGET),
                                                  "relies": {}})
            entry["relies"][sid] = how
    return {"solutions": solutions, "ancestors": ancestors, "dependents": dependents, "knowledge": knowledge}
