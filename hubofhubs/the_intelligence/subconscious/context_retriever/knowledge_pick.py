"""Which of one solution's knowledge cards bear on a request: what the selected Context Retriever picks from them, then what Intuition offered
among them, with a person's own words always first.

Not every item goes into a solution's prompt: knowledge that is relevant depends on the situation, so the retriever reads the request against
that solution's own items only (one corpus per solution, so a crowded solution cannot push a quiet one's items out). There is no count quota:
the retriever's own token budget and its abstention decide. An item whose source is a person is always kept, since a person's feedback weighs
most and is quoted as said. With no retriever the items come in the records' own rank order. Standard library plus the hub."""
from typing import Any, List, Mapping, Optional, Sequence

from hubofhubs.the_body.internal_context.card_store.card import Card

PERSON = "source-kind:person"


def hit_key(hit: Any) -> str:
    return str(hit.get("file") if isinstance(hit, Mapping) else getattr(hit, "file", ""))


def pick(request: str, cards: Sequence[Card], retriever: Optional[Any] = None, offered: Sequence[str] = (), budget_tokens: int = 1500,
         solution_name: str = "") -> List[Card]:
    """The cards to put under "Knowledge that bears on this", best first: a person's items, the retriever's picks, then Intuition's offers."""
    by_id = {c.id: c for c in cards}
    chosen: List[str] = [c.id for c in cards if PERSON in c.tags]
    if retriever is None:
        chosen += [c.id for c in cards]
    else:
        query = f"{request}\n{solution_name}".strip()
        for hit in retriever.retrieve(query, {c.id: c.text for c in cards}, budget_tokens) or ():
            chosen.append(hit_key(hit))
        chosen += [cid for cid in offered if cid in by_id]
    seen: List[str] = []
    for cid in chosen:
        if cid in by_id and cid not in seen:
            seen.append(cid)
    return [by_id[cid] for cid in seen]


def section(cards: Sequence[Card]) -> str:
    """The prompt section for the picked cards, or "" when none was picked."""
    if not cards:
        return ""
    return "## Knowledge that bears on this\n" + "\n".join("- " + c.text for c in cards)
