"""The hub's own card: the unit a card store keeps. Plain data, no behaviour, nothing consumer-specific."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Card:
    id: str                       # the caller's stable id; adding the same id again replaces the card
    text: str                     # what is remembered
    source: str = ""              # where it came from (a name or a link the caller understands)
    tags: Tuple[str, ...] = ()    # caller-defined labels, matched exactly by search(tag=...)
