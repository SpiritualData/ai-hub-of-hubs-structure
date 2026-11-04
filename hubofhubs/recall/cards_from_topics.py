"""Free topic-card builders: cards that group the files of one topic, made without a model.

A topic card bundles the files that belong to one piece of work, so a task about that work finds them together. Two builders group
files by structure and keep to a size cap (``cap`` files per card, a file in one card):

``CochangeTopicCards`` groups files that changed together in the same commits of a recorded history (``history`` is a list of
``{subject, files}``; the default is the committed history of the topic cases of cards-from-files, which ends before every test case). The
subjects of the commits that changed a group's files together are written into its description: a topic named in the words people
used when they changed it.
``ImportGraphTopicCards`` groups files that import each other, read from the source in the folder it is handed.

Both give the files no group holds folder-sized cards (``backfill``), so every file is reachable. Neither calls a model.
"""
from __future__ import annotations

import ast
import hashlib
import json
import posixpath
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation

from .cards_from_files import file_card, group_card
from .topic_clusters import add_pair, agglomerate, folder_chunks

HISTORY_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "cards_from_files" / "datasets" / "topic_cases" / "cochange_history.json"
CARD_CAP = 8            # files in one topic card
MIN_SUPPORT = 2         # commits a pair of files must have changed in together
SUBJECTS_PER_CARD = 6   # commit subjects written into a card
MAX_COMMIT_FILES = 30   # a commit with more files is a sweep and links nothing


def topic_cards(root: Path, groups: Sequence[Sequence[str]], prefix: str, said: Optional[Mapping[int, List[str]]] = None) -> List[Dict[str, Any]]:
    """One card per group, in group order; ``said[i]`` (commit subjects) is added to the description of group ``i``."""
    base = Path(root)
    singles = {path: file_card(base, path) for group in groups for path in group}
    cards = []
    for number, group in enumerate(groups):
        card = group_card(base, f"{prefix}-{number:04d}", list(group), singles)
        if said and said.get(number):
            card["description"] = " ".join([card["description"]] + said[number]).strip()
        cards.append(card)
    return cards


def load_history(path: Path) -> List[Dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["commits"]


@implementation("cards-from-files", "cochange_topic_cards")
class CochangeTopicCards:
    """Topic cards from co-change: files changed together in at least ``min_support`` commits of a recorded history are one card
    (at most ``cap`` files, a file in one card); the commit subjects that changed them together are the card's topic words; files with
    no co-change get folder cards when ``backfill`` is true."""
    REQUIRES = ()

    def __init__(self, history: str = "", cap: int = CARD_CAP, min_support: int = MIN_SUPPORT, backfill: bool = True):
        self.commits = load_history(Path(history) if history else HISTORY_FILE)
        self.cap, self.min_support, self.backfill = cap, min_support, backfill

    def groups(self, files: Sequence[str]) -> List[List[str]]:
        known, weights, support = set(files), {}, {}
        for commit in self.commits:
            changed = sorted(set(f for f in commit["files"] if f in known))
            if not 2 <= len(changed) <= MAX_COMMIT_FILES:
                continue
            for i, a in enumerate(changed):
                for b in changed[i + 1:]:
                    add_pair(weights, a, b, 1.0 / (len(changed) - 1))
                    support[(a, b)] = support.get((a, b), 0) + 1
        supported = {pair: weight for pair, weight in weights.items() if support[pair] >= self.min_support}
        return agglomerate(supported, self.cap)

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]:
        groups = self.groups(files)
        listed = {f for group in groups for f in group}
        subjects = []
        for group in groups:
            members = set(group)
            chosen = [c["subject"] for c in self.commits if len(members & set(c["files"])) >= 2]
            subjects.append(list(dict.fromkeys(chosen))[:SUBJECTS_PER_CARD])
        cards = topic_cards(Path(root), groups, "cochange", dict(enumerate(subjects)))
        if self.backfill:
            cards += topic_cards(Path(root), folder_chunks([f for f in files if f not in listed], self.cap), "folder")
        return cards


def module_name(path: str) -> str:
    parts = path[:-3].split("/")
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def imported_files(root: Path, path: str, by_module: Mapping[str, str]) -> List[str]:
    """The corpus files that the source of ``path`` imports (absolute and relative imports, and imported submodules)."""
    try:
        tree = ast.parse((root / path).read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return []
    package = module_name(path).split(".")
    if not path.endswith("__init__.py"):
        package = package[:-1]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = package[:len(package) - node.level + 1] if node.level else []
            stem = ".".join(base + ([node.module] if node.module else []))
            names = [stem] + [f"{stem}.{alias.name}" if stem else alias.name for alias in node.names]
        else:
            continue
        found += [by_module[n] for n in names if n in by_module]
    return found


@implementation("cards-from-files", "import_graph_topic_cards")
class ImportGraphTopicCards:
    """Topic cards from the import graph: files that import each other are one card (at most ``cap`` files, a file in one card), the
    most connected pairs first; files that import nothing in the corpus get folder cards when ``backfill`` is true."""
    REQUIRES = ()

    def __init__(self, cap: int = CARD_CAP, backfill: bool = True):
        self.cap, self.backfill = cap, backfill

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]:
        base = Path(root)
        by_module = {module_name(f): f for f in files}
        weights: Dict[Any, float] = {}
        for path in files:
            for other in set(imported_files(base, path, by_module)):
                if other != path:
                    add_pair(weights, path, other, 1.0 + (0.5 if posixpath.dirname(path) == posixpath.dirname(other) else 0.0))
        groups = agglomerate(weights, self.cap)
        listed = {f for group in groups for f in group}
        cards = topic_cards(base, groups, "imports")
        if self.backfill:
            cards += topic_cards(base, folder_chunks([f for f in files if f not in listed], self.cap), "folder")
        return cards
