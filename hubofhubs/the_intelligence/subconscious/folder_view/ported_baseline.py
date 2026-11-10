"""Folder View arm ``ported_baseline``: the selection the hub's own work harness used before this solution existed, ported as it was.

Skipping is a fixed list of folder names, hidden folders and a virtual environment's ``pyvenv.cfg``. The files in view are the ones the goal or
context names; then the whole folder when it fits the budget; then, for a small folder, a few files that share words with the goal; and nothing
unasked for a corpus of more than ``LEXICAL_FILES`` files. It is the baseline the better arms are scored against. No model call."""
from __future__ import annotations

import os
import re
from typing import Any, List, Mapping, Sequence, Set

from esoi import implementation

from hubofhubs.the_intelligence.subconscious.folder_view import naming
from hubofhubs.the_intelligence.subconscious.folder_view.choice import FolderChoice, LeftOut, Pick
from hubofhubs.the_intelligence.subconscious.folder_view.judgment import HEAD_CHARS, looks_binary, small_text

SKIPPED_FOLDERS = (".git", "__pycache__", "node_modules")
LEXICAL_FILES = 200                # above this many files, words shared with the goal no longer tell which files matter
LARGE_FOLDER_FILL = 24_000         # characters of likely files shown when the folder is too large to show whole
RELEVANT_SCORE = 3                 # a file needs a word of the goal in its path, or three in its opening, to be shown unasked
COMMON_WORDS = frozenset("this that with from have will your what which when where there their them then than they into every each about folder file files using write make report tell goal should must also only does done after before been were being more most some such very just like over under between".split())


@implementation("folder-view", "ported_baseline")
class PortedBaseline:
    """Named files, the whole folder when it fits, shared words for a small folder, nothing unasked for a corpus."""
    REQUIRES = ()

    def choose(self, goal: str, context: str, root: str, budget_chars: int = 100000, trail: Sequence[Mapping[str, Any]] = (),
               file_limit: int = 5000) -> FolderChoice:
        out = FolderChoice()
        files = self.walk(root, file_limit, out)
        texts = [(rel, size) for rel, size in files if size <= naming.FILE_LIMIT and self.readable(root, rel)]
        out.scanned = len(texts)
        text = goal + "\n" + context
        picks: List[Pick] = []
        named = naming.named_in(text, [rel for rel, _ in texts])
        for rel in naming.named_paths(text, root):
            if rel not in named:
                named.append(rel)
        used = 0
        for rel in named:
            size = min(naming.size_of(root, rel), budget_chars)
            picks.append(Pick(rel, "named in the goal or context", size, named=True))
            used += size
        taken = set(named)
        rest = [(rel, size) for rel, size in texts if rel not in taken]
        fill = budget_chars
        if used + sum(size for _, size in rest) <= budget_chars:
            ranked = sorted(rest, key=lambda f: f[1])
            why = "the whole folder fits in the view"
        elif len(texts) > LEXICAL_FILES:
            ranked, why = [], ""
        else:
            words = {w for w in re.findall(r"[a-z0-9]{4,}", text.lower()) if w not in COMMON_WORDS}
            scored = [(self.relevance(root, rel, words), rel, size) for rel, size in rest]
            ranked = [(rel, size) for score, rel, size in sorted(scored, key=lambda f: (-f[0], f[2])) if score >= RELEVANT_SCORE]
            why = "shares words with the goal"
            fill = min(budget_chars, used + LARGE_FOLDER_FILL)
        for rel, size in ranked:
            if used + min(size, budget_chars) > fill:
                continue
            picks.append(Pick(rel, why, min(size, budget_chars)))
            used += min(size, budget_chars)
        out.picks = picks
        return out

    def walk(self, root: str, limit: int, out: FolderChoice) -> List[tuple]:
        found: List[tuple] = []
        level = [(root, "")]
        while level and len(found) < limit:
            deeper = []
            for folder, rel_folder in level:
                try:
                    entries = sorted(os.scandir(folder), key=lambda e: e.name)
                except OSError:
                    continue
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        rel = (rel_folder + "/" if rel_folder else "") + entry.name
                        if entry.is_dir():
                            if entry.name in SKIPPED_FOLDERS or entry.name.startswith(".") or os.path.exists(os.path.join(entry.path, "pyvenv.cfg")):
                                out.left_out.append(LeftOut(rel + "/", "skipped by name or hidden or a virtual environment", "name"))
                            else:
                                deeper.append((entry.path, rel))
                        elif entry.is_file() and len(found) < limit:
                            found.append((rel, entry.stat().st_size))
                    except OSError:
                        continue
                if len(found) >= limit:
                    break
            level = deeper
        return sorted(found, key=lambda f: (f[0].count("/"), f[0]))

    def readable(self, root: str, rel: str) -> bool:
        path = os.path.join(root, rel)
        return not looks_binary(path)

    def relevance(self, root: str, rel: str, words: Set[str]) -> int:
        if not words:
            return 0
        head = small_text(os.path.join(root, rel), HEAD_CHARS)
        path_words = set(re.findall(r"[a-z0-9]{4,}", rel.lower()))
        head_words = set(re.findall(r"[a-z0-9]{4,}", head.lower()))
        return 3 * len(words & path_words) + len(words & head_words)
