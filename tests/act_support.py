"""Test doubles for the act arms: a directory writer with the boundary the arms rely on, and a fixed tier table. Tests only."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from hubofhubs.ports.deep import WriteResult

SECRETISH = (".env", ".pem", ".key")


class DirectoryWriter:
    """A ``FileWriter`` confined to ``root``: refuses paths outside it, protected names and directories, and copies what it replaces
    into ``backup_dir``. ``resolve`` is the boundary an arm pre-screens a candidate path with."""

    def __init__(self, root: str, *, backup_dir: Optional[str] = None):
        self.root = Path(root).resolve()
        self.backup_dir = Path(backup_dir) if backup_dir else None

    def resolve(self, rel_path: str) -> Optional[Path]:
        try:
            path = (self.root / rel_path).resolve()
            path.relative_to(self.root)
        except (ValueError, OSError):
            return None
        return None if path.name.startswith(".env") or path.suffix in SECRETISH else path

    def read_file(self, rel_path: str) -> Optional[str]:
        path = self.resolve(rel_path)
        return path.read_text(encoding="utf-8") if path is not None and path.is_file() else None

    def write_file(self, rel_path: str, content: str) -> WriteResult:
        path = self.resolve(rel_path)
        if path is None or path.is_dir():
            return WriteResult(ok=False, rel_path=rel_path, error="path is outside the writable root, or is a protected file")
        existed = path.is_file()
        backup = None
        if existed and self.backup_dir is not None:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup = self.backup_dir / f"{len(list(self.backup_dir.iterdir()))}-{path.name}"
            shutil.copyfile(path, backup)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return WriteResult(ok=True, rel_path=rel_path, bytes_written=len(content.encode("utf-8")), created=not existed,
                           backup_path=str(backup) if backup else None)


class FixedTiers:
    """A ``TierResolving`` that answers from a table."""

    def __init__(self, table=None):
        self.table = table or {"fast": "model-fast", "balanced": "model-balanced", "quality": "model-quality", "best": "model-best"}

    def resolve_tier(self, tier: str) -> str:
        return self.table[tier]
