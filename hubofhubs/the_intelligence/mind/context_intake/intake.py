"""Context Intake: the one intake of the Mind. It takes what the Subconscious prepared (recalled cards, what Intuition offered, the picked
pieces of files), what the World brought (a search answer and its sources) and the instructions that apply to the request (chosen within a token budget
and counted, ``doctrine.py``) and returns one view the Planner reads. It only merges and
labels where each part came from; picking is the Subconscious's job and the formatting of the picked text stays where the picks were made.
Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, List, Mapping, Optional

from esoi import implementation

from hubofhubs.the_intelligence.mind.context_intake.doctrine import within_budget


def line(label: str, text: str) -> str:
    return f"[{label}] {' '.join(str(text).split())}"


@implementation("context-intake", "one_view")
class OneView:
    """Merges prepared and outside information into one labelled view, each line naming where it came from, and lists the sources."""
    REQUIRES = ()     # pure merging

    def take(self, request: str, prepared: Optional[Mapping[str, Any]] = None, outside: Optional[Mapping[str, Any]] = None,
             instructions: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        prepared, outside, instructions = prepared or {}, outside or {}, instructions or {}
        lines: List[str] = []
        sources: List[Dict[str, Any]] = []
        for card in prepared.get("cards") or ():
            lines.append(line("card " + card.id, card.text))
            sources.append({"kind": "card", "id": card.id, **({"source": card.source} if card.source else {})})
        for piece in prepared.get("pieces") or ():
            text = getattr(piece, "text", "") or str(getattr(piece, "first_line", ""))
            lines.append(line("file " + str(getattr(piece, "file", "")), text))
            sources.append({"kind": "file", "id": str(getattr(piece, "id", "")), "file": str(getattr(piece, "file", ""))})
        for offered in prepared.get("offered") or ():
            lines.append(line("offered", offered.get("text", "")))
            sources.append({"kind": "offered", "id": str(offered.get("id", ""))})
        if outside.get("answer"):
            lines.append(line("world", outside["answer"]))
        for item in outside.get("items") or ():
            sources.append({"kind": "world", "url": item.get("url", ""), "title": item.get("title", "")})
        chosen = within_budget(instructions.get("rules") or (), instructions.get("situation") or {}, int(instructions.get("budget_tokens") or 0))
        if chosen.text:
            lines.append(line("instructions", chosen.text))
        return {"request": request, "view": "\n".join(lines), "sources": sources,
                "instructions": {"included": list(chosen.included), "excluded": list(chosen.excluded), "tokens": chosen.tokens}}
