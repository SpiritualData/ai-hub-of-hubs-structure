"""File Reading (World, a Tools category): reads text files from a folder and lists them, the world-facing half of working with files that
Cards From Files needs (File Editing is the writing half). It never leaves the folder it is given, skips what is not text, and caps what it
returns so one read cannot flood a context. Standard library plus the hub and ``esoi``."""
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from esoi import implementation

MAX_BYTES = 200_000
SKIPPED = {".git", "__pycache__", "node_modules", ".venv"}


def inside(root: Path, path: str) -> Path:
    target = (root / path).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        raise ValueError(f"{path!r} is outside the folder")
    return target


@implementation("read-files", "folder_reader")
class FolderReader:
    """Lists and reads the text files of one folder, never outside it."""
    REQUIRES = ()     # the local disk

    def list(self, root: str, suffixes: Sequence[str] = ()) -> Sequence[str]:
        base = Path(root)
        found: List[str] = []
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(base)
            if path.is_file() and not SKIPPED & set(relative.parts) and (not suffixes or path.suffix in suffixes):
                found.append(relative.as_posix())
        return found

    def read(self, root: str, paths: Sequence[str] = ()) -> Mapping[str, str]:
        base = Path(root)
        out: Dict[str, str] = {}
        for path in paths or self.list(root):
            target = inside(base, path)
            if not target.is_file() or target.stat().st_size > MAX_BYTES:
                continue
            try:
                out[path] = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        return out
