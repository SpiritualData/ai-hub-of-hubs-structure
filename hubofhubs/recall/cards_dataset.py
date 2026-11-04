"""A persisted card build: the cards of one recorded run, read back from a JSON document, checked, and replayed for free.

A paid builder's cards cost money to make once. ``write``-time facts (the build id, the pin the build was made on, the model calls,
tokens and cost) and the cards themselves live in one committed document, and ``load_dataset`` refuses it when its cards no longer
hash to the digest the document carries. ``check_pin`` refuses a replay on any corpus other than the one the build was made on.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

PIN_KEYS = ("qar_commit", "hub_commit", "cases_sha256")


class DatasetError(RuntimeError):
    """A persisted build that cannot be trusted or replayed here; the message says which check failed."""


def cards_digest(cards: Sequence[Mapping[str, Any]]) -> str:
    """The sha256 of the cards as canonical JSON (sorted keys, no spaces), so formatting of the document never matters."""
    text = json.dumps(list(cards), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_dataset(path: Path) -> Dict[str, Any]:
    """The document at ``path`` with its cards checked: a digest that differs or a repeated card id is a ``DatasetError``."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    cards = document.get("cards")
    if not isinstance(cards, list) or not cards:
        raise DatasetError(f"{path} holds no cards")
    if cards_digest(cards) != document.get("cards_sha256"):
        raise DatasetError(f"the cards of {path} do not match the digest the document carries; the dataset was edited or damaged")
    ids = [card.get("id") for card in cards]
    if len(set(ids)) != len(ids) or not all(ids):
        raise DatasetError(f"{path} has a card without an id or two cards with the same id")
    return document


def check_pin(document: Mapping[str, Any], pin: Mapping[str, Any], files: Sequence[str] = ()) -> None:
    """Refuse a replay unless ``pin`` (the corpus pin in force) names the commits and cases the build was made on, and, when ``files``
    is given, the corpus walk is the one the build saw (its sorted list hashes to the recorded ``files_sha256``)."""
    built = document["pin"]
    wrong = [key for key in PIN_KEYS if key in pin and pin[key] != built.get(key)]
    if wrong:
        raise DatasetError("the build was made on another corpus: " + ", ".join(f"{k} is {pin[k]!r}, the build used {built.get(k)!r}" for k in wrong))
    if files:
        digest = hashlib.sha256("\n".join(sorted(files)).encode("utf-8")).hexdigest()
        if digest != built.get("files_sha256"):
            raise DatasetError("the corpus files differ from the ones the build was made on (files_sha256)")


def card_copies(document: Mapping[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
    """Fresh copies of the cards (so a consumer cannot change the document), their ids prefixed when ``prefix`` is given."""
    copies = json.loads(json.dumps(document["cards"]))
    for card in copies:
        card["id"] = prefix + card["id"]
    return copies
