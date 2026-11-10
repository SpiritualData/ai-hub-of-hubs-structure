"""What the hub says about itself: its five parts and what each is for, read from Role Understanding (the hub's own records), so a question about the hub
("what can you do?") is answered from what the hub holds and never from a web search. A part whose record is not packaged (an installed copy carries
no records) is described by the first sentence of its interface. Standard library plus the hub and ``esoi``."""
from typing import Any, List

from esoi import declared_entry

PARTS = (("the-self", "The Self"), ("the-body", "Body"), ("the-intelligence", "Intelligence"), ("the-world", "World"), ("the-consciousness", "Consciousness"))

CLOSING = ("Ask me a question and I look up what needs current facts on the web, ask me to read or change a file in a folder, or give me a task in several steps. "
           "When a choice is yours to make I ask you instead of guessing.")


def first_sentence(text: str, limit: int = 200) -> str:
    """The first sentence of ``text``, cut at a word when it runs past ``limit`` characters."""
    flat = " ".join((text or "").split()).replace("``", "")
    if not flat:
        return ""
    first = flat.split(". ")[0].rstrip(".")
    if len(first) > limit:
        first = first[:limit].rsplit(" ", 1)[0].rstrip(",;:") + " ..."
    return first + "."


def purpose_of(roles: Any, part: str) -> str:
    """The recorded purpose of a part, else the first sentence of its interface, else nothing."""
    found = roles.state_role(part)
    if found.get("stated") and found.get("purpose"):
        return first_sentence(str(found["purpose"]))
    from hubofhubs.the_self.assembler.resolution import HUB     # late: the hub's seats load only when asked
    entry = declared_entry(HUB, part)
    return first_sentence(getattr(entry.interface, "__doc__", "") if entry is not None else "")


def describe_hub(roles: Any) -> str:
    """One paragraph per part, then what to ask."""
    lines: List[str] = ["I am a hub of hubs: one assistant put together from five parts, each part the best-measured arm for its job."]
    for part, name in PARTS:
        purpose = purpose_of(roles, part)
        if purpose:
            lines.append(f"- {name}: {purpose}")
    lines.append(CLOSING)
    return "\n".join(lines)
