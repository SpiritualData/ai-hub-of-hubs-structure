"""Cards from a solution's records: the solution's stable part as one managed card, and one card per knowledge item that accrues onto it.

The records stay the source of truth: the managed card is rebuilt from them, so a card writer never edits it (tag ``managed``), while new items
are new cards with the same ``solution:<id>`` tag. An item that is superseded, contradicted or expired is kept as a quarantined card (tag
``quarantined``), never deleted, so what replaced it and why stay readable; a quarantined card is never picked for a prompt. Standard library."""
from typing import Any, List, Mapping, Sequence

from hubofhubs.the_body.internal_context.card_store.card import Card

MANAGED, QUARANTINED, KNOWLEDGE, STABLE = "managed", "quarantined", "knowledge", "solution-stable"


def solution_tag(sid: str) -> str:
    return "solution:" + sid


def card_id_of(item: Mapping[str, Any]) -> str:
    return "knowledge-" + str(item.get("id") or "")


def solution_card(sid: str, text: str, digest: str = "") -> Card:
    """The managed card of one solution: its stable part (definition, metric, selection, decisive results, connected solutions)."""
    return Card(id="solution-" + sid, text=text, source="records:" + sid + (("@" + digest) if digest else ""), tags=(solution_tag(sid), STABLE, MANAGED))


def item_text(item: Mapping[str, Any]) -> str:
    kind = str(item.get("kind") or "").strip()
    source = str(item.get("source") or "").strip()
    return (f"[{kind}] " if kind else "") + str(item.get("claim") or "").strip() + (f" (source: {source})" if source else "")


def knowledge_card(item: Mapping[str, Any], retired: bool = False) -> Card:
    """One knowledge item as a card, tagged with every solution it is linked to, its kind, its source kind and its status."""
    tags = [solution_tag(s) for s in item.get("solution_ids") or ()] + [KNOWLEDGE, "status:" + str(item.get("status") or "active")]
    tags += [f"kind:{item['kind']}"] if item.get("kind") else []
    tags += [f"source-kind:{item['source_kind']}"] if item.get("source_kind") else []
    tags += [QUARANTINED] if retired else []
    return Card(id=card_id_of(item), text=item_text(item), source=str(item.get("source") or ""), tags=tuple(tags))


def cards_of(sid: str, made: Mapping[str, Any]) -> List[Card]:
    """Every card of one solution's generated prompt: the managed card, the active items and the retired items (quarantined)."""
    return ([solution_card(sid, str(made.get("text") or ""), str(made.get("digest") or ""))]
            + [knowledge_card(item) for item in made.get("knowledge") or ()]
            + [knowledge_card(item, retired=True) for item in made.get("knowledge_inactive") or ()])


def active(cards: Sequence[Card]) -> List[Card]:
    """The knowledge cards that may be picked: not the managed card, never a quarantined one."""
    return [c for c in cards if KNOWLEDGE in c.tags and QUARANTINED not in c.tags]
