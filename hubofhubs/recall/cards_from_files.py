"""The ``cards-from-files`` arms that need no graph library: one card per file, and topic cards a model writes.

A card is the card-store record shape the context store reads: ``id``, ``keywords``, ``summary``, ``description``, ``weight``
and ``files`` (each ``{"path", "symbols", "sha256"}``). A builder proposes cards for the files of a folder and writes nothing.
``changed`` names the cards whose files differ on disk from what the card recorded, so a consumer rebuilds only those.

``PerFileSymbols`` is the free floor: one card per file, described by the file's docstrings and symbols. ``LlmTopicCards`` groups
files into topic cards with a model (the model is a constructor need, the ``call-a-model`` seat) and is a paid arm.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from esoi import implementation

from ..seats import ModelCalling
from .context_bootstrap_support import jaccard, merge_card_group
from .context_card_extraction import (
    SOURCE_FILE_WEIGHT, TEST_FILE_WEIGHT, build_rich_summary, discover_areas, extract_symbols, extract_topic_cards,
    is_test_path, path_slug,
)

AREA_CHUNK_FILES = 150     # files shown to the model per area-discovery call
DUPLICATE_OVERLAP = 0.6    # topic cards whose file sets overlap at least this much (Jaccard) are one card


def file_digest(path: Path) -> str:
    """The sha256 of a file's bytes, or an empty string when it cannot be read (a card of a vanished file is stale)."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def file_entry(root: Path, rel: str) -> Dict[str, Any]:
    """A card's record of one file: its path, its symbols and the digest it had when the card was built."""
    path = root / rel
    return dict(path=rel, symbols=extract_symbols(path), sha256=file_digest(path))


def card_weight(paths: Iterable[str]) -> float:
    """A card of test files only is down-weighted, as the store does for a test file's own card."""
    paths = list(paths)
    return TEST_FILE_WEIGHT if paths and all(is_test_path(p) for p in paths) else SOURCE_FILE_WEIGHT


def file_card(root: Path, rel: str) -> Dict[str, Any]:
    """The one-file card of ``rel``: summary and description from its docstrings and symbols."""
    entry = file_entry(root, rel)
    summary, description = build_rich_summary(rel, root / rel, entry["symbols"])
    return dict(id=path_slug(rel), keywords=[], summary=summary, description=description, files=[entry], weight=card_weight([rel]))


def group_card(root: Path, card_id: str, members: Sequence[str], singles: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """One card for a group of files, in the order given: the members' summaries and descriptions joined, each member's own
    symbols and digest kept. ``singles`` holds the one-file card of each member."""
    return dict(id=card_id, keywords=[], summary=" ".join(singles[m]["summary"] for m in members),
                description=" ".join(singles[m]["description"] for m in members),
                files=[dict(singles[m]["files"][0]) for m in members], weight=card_weight(members))


def changed_cards(root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]:
    """Ids of the cards that name a file whose bytes differ from the digest recorded in the card, or that no longer exists."""
    base, stale = Path(root), []
    for card_id, card in cards.items():
        for entry in card.get("files", []):
            path = entry["path"] if isinstance(entry, Mapping) else entry
            recorded = entry.get("sha256", "") if isinstance(entry, Mapping) else ""
            if recorded and file_digest(base / path) != recorded:
                stale.append(card_id)
                break
    return sorted(stale)


def kept_card(card: Mapping[str, Any], root: Path) -> bool:
    """Whether an existing card still describes its files exactly (every file has a recorded digest that matches the disk)."""
    entries = card.get("files", [])
    return bool(entries) and all(isinstance(e, Mapping) and e.get("sha256") and file_digest(root / e["path"]) == e["sha256"] for e in entries)


@implementation("cards-from-files", "per_file_symbols")
class PerFileSymbols:
    """One card per file, described by the file's docstrings and symbols: the free floor every grouping builder has to beat.

    A card of ``existing`` that still describes its file (same digest) is returned unchanged, so ids and any later edits stay."""
    REQUIRES = ()

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]:
        base = Path(root)
        by_path = {e["path"]: dict(card) for card in existing.values() if len(card.get("files", [])) == 1 and kept_card(card, base)
                   for e in card["files"]}
        return [by_path.get(rel) or file_card(base, rel) for rel in files]

    def changed(self, root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]:
        return changed_cards(root, cards)


@implementation("cards-from-files", "llm_topic_cards")
class LlmTopicCards:
    """Model-written topic cards: the files are cut into chunks, a model names the areas of each chunk, then writes topic cards for
    each area from a sample of its files; cards that cover mostly the same files are merged into one.

    The model is a constructor need typed with the call-a-model seat (``hubofhubs.seats.ModelCalling``); every build spends calls."""
    REQUIRES = ()

    def __init__(self, provider: ModelCalling, model: str = ""):
        self.provider = provider
        self.model = model

    def propose(self, root: Path, files: Sequence[str]) -> List[Dict[str, Any]]:
        """The model's topic cards for ``files``, each ``{id, name, keywords, summary, files}``, duplicates merged."""
        allowed = set(files)
        areas: List[Dict[str, Any]] = []
        for start in range(0, len(files), AREA_CHUNK_FILES):
            areas += discover_areas(list(files[start:start + AREA_CHUNK_FILES]), self.provider, self.model)
        cards: List[Dict[str, Any]] = []
        for area in areas:
            cards += extract_topic_cards(area, allowed, self.provider, self.model, walk_root=root)
        return merge_duplicates(cards)

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]:
        base = Path(root)
        kept = [dict(card) for card in existing.values() if kept_card(card, base)]
        covered = {e["path"] for card in kept for e in card["files"]}
        todo = [f for f in files if f not in covered]
        singles = {rel: file_card(base, rel) for rel in todo}
        made = []
        for card in self.propose(base, todo) if todo else []:
            members = [f for f in card["files"] if f in singles]
            if not members:
                continue
            record = group_card(base, card["id"], members, singles)
            record.update(keywords=list(card.get("keywords", [])), summary=card.get("summary") or record["summary"], name=card["name"])
            made.append(record)
        return kept + made

    def changed(self, root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]:
        return changed_cards(root, cards)


def merge_duplicates(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge topic cards whose file sets overlap by at least ``DUPLICATE_OVERLAP`` (the first card of a group keeps its id, name and
    summary), and give a repeated id a numeric suffix so every card keeps its own."""
    groups: List[List[Dict[str, Any]]] = []
    for card in cards:
        files = set(card["files"])
        for group in groups:
            if jaccard(files, {f for member in group for f in member["files"]}) >= DUPLICATE_OVERLAP:
                group.append(card)
                break
        else:
            groups.append([card])
    merged, seen = [], set()
    for group in groups:
        card = merge_card_group(group)
        base, n = card["id"], 1
        while card["id"] in seen:
            n += 1
            card["id"] = f"{base}-{n}"
        seen.add(card["id"])
        merged.append(card)
    return merged
