"""What the goal and the context name: files by path or by file name, and paths deeper than a scan went. Shared by every Folder View arm."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Sequence, Tuple

from hubofhubs.the_world.tools.file_reading.read_files import inside

PATH_TOKEN = re.compile(r"(?<![\w/.-])/?(?:[\w.-]+/)+[\w.-]+\.\w{1,6}(?![\w])")      # a path with at least one folder and a file suffix
FILE_LIMIT = 200_000                                                                    # a larger file is not shown unasked


def mentions(text: str, name: str) -> bool:
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?!\w)", text) is not None


def named_in(text: str, files: Sequence[str]) -> List[str]:
    """The files of the scan that ``text`` names by path or by file name, in the order of ``files``."""
    return [rel for rel in files if (rel in text and mentions(text, rel)) or (rel.rsplit("/", 1)[-1] in text and mentions(text, rel.rsplit("/", 1)[-1]))]


def named_paths(text: str, root: str) -> List[str]:
    """Relative paths ``text`` gives in full that exist as files under ``root`` (including ones a scan did not reach or left out)."""
    found: List[str] = []
    base = Path(root)
    for token in dict.fromkeys(PATH_TOKEN.findall(text)):
        try:
            path = inside(base, token.strip("./") if not token.startswith("/") else token)
        except (ValueError, OSError):
            continue
        rel = os.path.relpath(path, base.resolve()).replace(os.sep, "/")
        try:
            if path.is_file() and path.stat().st_size <= FILE_LIMIT:
                found.append(rel)
        except OSError:
            continue
    return found


def size_of(root: str, rel: str) -> int:
    try:
        return (Path(root) / rel).stat().st_size
    except OSError:
        return 0
