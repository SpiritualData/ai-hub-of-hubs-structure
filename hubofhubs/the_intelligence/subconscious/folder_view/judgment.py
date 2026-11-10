"""Folder judgment: which folders and files of a working folder are never worth scanning, and which are risky to read, decided by evidence in the
folder (a project file beside it, a marker inside it, what its files are) and not by a name list alone.

The data is ``markers.py`` (one row per kind of folder or file, so a new ecosystem is a row); the rules here are small and fixed:

* a risky verdict (credentials, backups, other people's private data) comes first and wins over any other;
* a table row applies when its name matches and its evidence holds (a row with no evidence lists a name that is nothing else);
* a folder is also left out on evidence alone: a virtual environment (``pyvenv.cfg``, ``bin/activate``, ``conda-meta``), a cache that says so
  (``CACHEDIR.TAG``, a ``.gitignore`` of ``*``), or a name the project's own ``.gitignore`` lists;
* any other hidden folder is tool or personal state and is left out as such.

``scan`` walks a folder level by level with these rules and returns the files, the folders left out with the reason, and the head of each file read.
Standard library only; nothing here reads the environment.
"""
from __future__ import annotations

import fnmatch
import functools
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, NamedTuple, Optional, Sequence, Set, Tuple

from hubofhubs.the_intelligence.subconscious.folder_view import markers
from hubofhubs.the_intelligence.subconscious.folder_view.choice import LeftOut

HEAD_CHARS = 2048
SNAPSHOT_FILES = 5000


class Verdict(NamedTuple):
    kind: str
    reason: str
    risky: bool = False


@dataclass
class Scan:
    """``files`` are ``(relative path, size, mtime in ns)`` shallow first; ``heads`` the opening text of each readable file (empty unless ``inspect``)."""
    files: List[Tuple[str, int, float]] = field(default_factory=list)
    left_out: List[LeftOut] = field(default_factory=list)
    skipped: Dict[str, int] = field(default_factory=dict)
    heads: Dict[str, str] = field(default_factory=dict)


@functools.lru_cache(maxsize=None)
def compiled(patterns: Tuple[str, ...]) -> "re.Pattern[str]":
    """One regular expression for a tuple of case-insensitive name patterns (the table is matched against every file, so it is compiled once)."""
    return re.compile("|".join(fnmatch.translate(p.lower()) for p in patterns) or "(?!)")


def matches(name: str, patterns: Sequence[str]) -> bool:
    return compiled(tuple(patterns)).match(name.lower()) is not None


def present(token: str, folder: str, names: Set[str]) -> bool:
    """Whether the entry (or entries, ``a+b`` needs all; a ``/`` is a path under the folder) a marker asks for exists in ``folder``."""
    for part in token.split("+"):
        if "/" in part:
            if not os.path.exists(os.path.join(folder, part)):
                return False
        elif not any(compiled((part,)).match(n) for n in names):
            return False
    return True


def evidence_holds(marker: markers.Marker, folder: str, own: Set[str], parent: Set[str]) -> bool:
    if not marker.beside and not marker.inside:
        return True
    parent_folder = os.path.dirname(folder)
    return any(present(t, parent_folder, parent) for t in marker.beside) or any(present(t, folder, own) for t in marker.inside)


def small_text(path: str, chars: int = 200) -> str:
    try:
        with open(path, "rb") as handle:
            return handle.read(chars).decode("utf-8", errors="ignore")
    except OSError:
        return ""


def secret_name(name: str) -> bool:
    low = name.lower()
    if matches(low, markers.SECRET_TEMPLATES) or os.path.splitext(low)[1] in markers.NOT_SECRET_SUFFIXES:
        return False
    return matches(low, markers.SECRET_FILES)


def gitignore_names(root: str) -> Tuple[Set[str], Set[str]]:
    """``(names, paths)`` the project's own ``.gitignore`` lists as plain folder names or plain relative paths (patterns with wildcards are not read)."""
    names: Set[str] = set()
    paths: Set[str] = set()
    for line in small_text(os.path.join(root, ".gitignore"), 20000).splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "!")) or any(c in line for c in "*?[") or line.startswith("**"):
            continue
        line = line.lstrip("/").rstrip("/")
        if line:
            (paths if "/" in line else names).add(line.lower())
    return names, paths


def folder_verdict(folder: str, name: str, rel: str, own: Set[str], parent: Set[str], ignored: Tuple[Set[str], Set[str]] = (set(), set())) -> Optional[Verdict]:
    """Why a folder is not worth scanning, or None. ``own`` and ``parent`` are the lower-case entry names of the folder and of its parent."""
    held = [n for n in own if secret_name(n) and not matches(n, markers.FILE_ONLY_SECRETS)]
    if held:
        return Verdict("risky", f"holds credentials or secrets ({sorted(held)[0]})", True)
    found = [m for m in markers.FOLDERS if matches(name, m.names) and evidence_holds(m, folder, own, parent)]
    for marker in sorted(found, key=lambda m: not m.risky):
        return Verdict(marker.kind, marker.reason, marker.risky)
    if "pyvenv.cfg" in own or "conda-meta" in own or (("bin" in own or "scripts" in own) and
                                                         (os.path.exists(os.path.join(folder, "bin", "activate")) or os.path.exists(os.path.join(folder, "Scripts", "activate.bat")))):
        return Verdict("dependency", "a virtual environment (installed packages)")
    if "cachedir.tag" in own or (".gitignore" in own and small_text(os.path.join(folder, ".gitignore")).strip() == "*"):
        return Verdict("cache", "a cache that marks itself as not to be kept")
    if name.lower() in ignored[0] or rel.lower() in ignored[1]:
        return Verdict("generated", "listed in the project's own .gitignore")
    if name.startswith("."):
        return Verdict("hidden", "a hidden folder (tool or personal state)")
    return None


def secret_content(name: str, head: str) -> bool:
    if any(re.search(p, head) for p in markers.SECRET_CONTENT):
        return True
    return os.path.splitext(name.lower())[1] in markers.SETTING_SUFFIXES and re.search(markers.SECRET_SETTING, head) is not None


def file_verdict(name: str, size: int, head: Optional[str] = None) -> Optional[Verdict]:
    """Why a file is not worth reading, or None. ``head`` is the opening text when it was read (a file with a credential in it is risky)."""
    if secret_name(name):
        return Verdict("risky", "a credentials or key file", True)
    if head and secret_content(name, head):
        return Verdict("risky", "holds what looks like a credential", True)
    suffix = os.path.splitext(name.lower())[1]
    if matches(name, markers.BACKUP_FILES):
        return Verdict("risky", "a backup or mailbox copy", True)
    if matches(name, markers.GENERATED_FILES):
        return Verdict("generated", "generated bulk (lock file, minified or mapped bundle)")
    if suffix in markers.BINARY_SUFFIXES:
        return Verdict("binary", "binary or media file")
    if suffix in markers.DATA_SUFFIXES and size > markers.DATA_BYTES:
        return Verdict("generated", "large data dump")
    return None


def names_of(entries: Sequence[os.DirEntry]) -> Set[str]:
    return {e.name.lower() for e in entries}


def scan(root: str, limit: int = SNAPSHOT_FILES, inspect: bool = False, max_size: int = 0) -> Scan:
    """Walk ``root`` level by level (so a cap keeps the shallow files of a very large folder) applying the folder and file judgment. With ``inspect``
    each kept file's head is read once: a file that looks binary is passed over and one that holds a credential is left out as risky. A file larger
    than ``max_size`` (when given) is not listed. At most ``limit`` files."""
    out = Scan()
    ignored = gitignore_names(root)
    level: List[Tuple[str, str, Set[str]]] = [(root, "", set())]
    first = True
    while level and len(out.files) < limit:
        deeper: List[Tuple[str, str, Set[str]]] = []
        for folder, rel_folder, parent in level:
            try:
                entries = sorted(os.scandir(folder), key=lambda e: e.name)
            except OSError:
                continue
            own = names_of(entries)
            if not first:
                verdict = folder_verdict(folder, os.path.basename(folder), rel_folder, own, parent, ignored)
                if verdict:
                    out.left_out.append(LeftOut(rel_folder + "/", verdict.reason, verdict.kind, verdict.risky))
                    continue
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    rel = (rel_folder + "/" if rel_folder else "") + entry.name
                    if entry.is_dir():
                        deeper.append((entry.path, rel, own))
                    elif entry.is_file() and len(out.files) < limit:
                        stat = entry.stat()
                        head = None
                        if inspect and not (max_size and stat.st_size > max_size):
                            head = read_head(entry.path)
                        verdict = file_verdict(entry.name, stat.st_size, head)
                        if verdict and verdict.risky:
                            out.left_out.append(LeftOut(rel, verdict.reason, verdict.kind, True, True))
                        elif verdict:
                            out.skipped[verdict.kind] = out.skipped.get(verdict.kind, 0) + 1
                        elif inspect and (head is None or (max_size and stat.st_size > max_size)):
                            out.skipped["binary" if head is None else "large"] = out.skipped.get("binary" if head is None else "large", 0) + 1
                        else:
                            out.files.append((rel, stat.st_size, stat.st_mtime_ns))
                            if head is not None:
                                out.heads[rel] = head
                except OSError:
                    continue
            if len(out.files) >= limit:
                break
        first = False
        level = deeper
    out.files.sort(key=lambda f: (f[0].count("/"), f[0]))
    return out


def read_head(path: str) -> Optional[str]:
    """The first ``HEAD_CHARS`` bytes of a file as text, or None when it cannot be read or looks binary (one read)."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(HEAD_CHARS)
    except OSError:
        return None
    return None if b"\0" in data else data.decode("utf-8", errors="ignore")


def looks_binary(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            return b"\0" in handle.read(HEAD_CHARS)
    except OSError:
        return True


def path_verdict(root: str, rel: str) -> Optional[Verdict]:
    """The judgment for one named path: the first risky or unhelpful folder on its way down, else the file's own. For a goal that names a file
    deeper than a scan went or inside a folder the scan left out."""
    base = Path(root)
    parts = rel.split("/")
    ignored = gitignore_names(root)
    for depth in range(1, len(parts)):
        folder = base.joinpath(*parts[:depth])
        try:
            entries = list(os.scandir(folder))
            parent_entries = list(os.scandir(folder.parent))
        except OSError:
            return None
        verdict = folder_verdict(str(folder), parts[depth - 1], "/".join(parts[:depth]), names_of(entries), names_of(parent_entries), ignored)
        if verdict:
            return verdict
    try:
        size = (base / rel).stat().st_size
    except OSError:
        return None
    return file_verdict(parts[-1], size, small_text(str(base / rel), HEAD_CHARS))
