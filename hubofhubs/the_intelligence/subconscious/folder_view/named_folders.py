"""A folder the goal or the context names is strong evidence: what to show from it is its orienting files first, then the files its words point at.

``named`` finds the folders a text names (a path with or without a trailing slash at any depth, or a bare folder name that is unique in the tree and looks
like a name: it has an underscore or hyphen, or is next to the word folder or directory). ``unreached`` finds named paths the scan did not reach, which
the caller then scans directly. ``orienting`` decides, by evidence in the folder and not by one name list, which of its top-level files orient a worker:
a file by a name that says so (readme, context, goals, plan, index), a file every sibling folder also has, and the most recently changed files.
Standard library only."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Set, Tuple

from hubofhubs.the_intelligence.subconscious.folder_view import judgment
from hubofhubs.the_world.tools.file_reading.read_files import inside

ORIENTING_STEMS = frozenset("readme claude agents context goals goal plan plans index overview todo status summary contents about".split())
HOUR_NS = 3_600_000_000_000
RECENT_FILES = 2             # the files changed most recently in a folder count as orienting evidence
FOLDER_TOKEN = re.compile(r"(?<![\w/.-])(?:\./)?(?:[\w.-]+(?:/[\w.-]+)+/?|[\w.-]+/)")
BARE_TOKEN = re.compile(r"[A-Za-z][\w-]*")
BESIDE_FOLDER = re.compile(r"\b(?:folder|directory|dir)\s+([A-Za-z][\w-]*)|\b([A-Za-z][\w-]*)\s+(?:folder|directory|dir)\b")


def directories(paths: Sequence[str]) -> Dict[str, List[str]]:
    """``{folder path: its files}`` for every folder above any of the files (a file is listed under each folder above it)."""
    found: Dict[str, List[str]] = {}
    for rel in paths:
        parts = rel.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            found.setdefault("/".join(parts[:depth]), []).append(rel)
    return found


def clean(token: str) -> str:
    return token.strip().rstrip(".,;:)").lstrip("(").removeprefix("./").strip("/")


def named(text: str, dirs: Mapping[str, List[str]], limit: int = 3) -> List[str]:
    """The folders of ``dirs`` that ``text`` names, in order of appearance, at most ``limit``."""
    found: List[str] = []
    for token in FOLDER_TOKEN.findall(text):
        path = clean(token)
        if path in dirs and path not in found:
            found.append(path)
    by_name: Dict[str, List[str]] = {}
    for path in dirs:
        by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)
    beside = {g for pair in BESIDE_FOLDER.findall(text) for g in pair if g}
    for token in dict.fromkeys(BARE_TOKEN.findall(text)):
        if ("_" in token or "-" in token or token in beside) and len(by_name.get(token, [])) == 1 and by_name[token][0] not in found:
            found.append(by_name[token][0])
    return found[:limit]


def unreached(text: str, root: str, dirs: Mapping[str, List[str]], limit: int = 3) -> List[str]:
    """Folders ``text`` gives by path that exist under ``root`` though the scan did not list them (it stopped at its cap), and that are not themselves
    risky or in a risky folder; the caller scans them directly."""
    found: List[str] = []
    base = Path(root)
    for token in FOLDER_TOKEN.findall(text):
        path = clean(token)
        if not path or path in dirs or path in found:
            continue
        try:
            target = inside(base, path)
        except (ValueError, OSError):
            continue
        rel = os.path.relpath(target, base.resolve()).replace(os.sep, "/")
        if target.is_dir() and not judgment.path_verdict(root, rel + "/x"):
            found.append(rel)
    return found[:limit]


def orienting(folder: str, files: Sequence[str], mtimes: Mapping[str, float], dirs: Mapping[str, List[str]]) -> List[Tuple[str, str, bool]]:
    """``(path, why, strong)`` for the top-level files of ``folder`` that orient a worker, strongest evidence first; a file that is only among the most
    recently changed is not strong."""
    top = [rel for rel in files if rel.rsplit("/", 1)[0] == folder]
    parent = folder.rsplit("/", 1)[0] if "/" in folder else ""
    siblings = [d for d in dirs if d != folder and (d.rsplit("/", 1)[0] if "/" in d else "") == parent]
    shared: Dict[str, int] = {}
    for sibling in siblings:
        for name in {rel.rsplit("/", 1)[-1] for rel in dirs[sibling] if rel.rsplit("/", 1)[0] == sibling}:
            shared[name] = shared.get(name, 0) + 1
    stamps = sorted(mtimes.get(r, 0) for r in top)
    median = stamps[len(stamps) // 2] if stamps else 0
    recent = [r for r in sorted(top, key=lambda r: (-mtimes.get(r, 0), r))[:RECENT_FILES] if mtimes.get(r, 0) > median + HOUR_NS]      # clearly newer than most of the folder
    scored: List[Tuple[float, str, str]] = []
    for rel in top:
        name = rel.rsplit("/", 1)[-1]
        reasons = []
        score = 0.0
        if os.path.splitext(name)[0].lower() in ORIENTING_STEMS:
            score += 1.0
            reasons.append("a name that orients")
        if len(siblings) >= 2 and shared.get(name, 0) >= max(2, len(siblings) // 2) and not name.startswith("entry_"):
            score += 0.9
            reasons.append("every sibling folder has one")
        if rel in recent:
            score += 0.4
            reasons.append("among the most recently changed")
        if score:
            scored.append((score, rel, ", ".join(reasons)))
    return [(rel, why, score >= 0.9) for score, rel, why in sorted(scored, key=lambda t: (-t[0], t[1]))]
