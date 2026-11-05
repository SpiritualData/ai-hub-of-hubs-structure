"""A ``FileWriter`` confined to one folder: the grant of write access is naming that folder. Standard library only."""
import shutil
from pathlib import Path
from typing import Optional

from hubofhubs.the_world.tools.deep import WriteResult

SECRETISH = (".env", ".pem", ".key")


class FolderWriter:
    """Refuses paths outside ``root``, credential-like names and directories, and copies each file it replaces into ``backup_dir``
    (``<root>/.hubofhubs-backups`` unless given). ``resolve`` is the boundary an arm pre-screens a candidate path with."""

    def __init__(self, root: str, *, backup_dir: Optional[str] = None):
        self.root = Path(root).resolve()
        self.backup_dir = Path(backup_dir) if backup_dir else self.root / ".hubofhubs-backups"

    def resolve(self, rel_path: str) -> Optional[Path]:
        try:
            path = (self.root / rel_path).resolve()
            path.relative_to(self.root)
        except (ValueError, OSError):
            return None
        return None if path.name.startswith(".env") or path.suffix in SECRETISH else path

    def read_file(self, rel_path: str) -> Optional[str]:
        path = self.resolve(rel_path)
        try:
            return path.read_text(encoding="utf-8") if path is not None and path.is_file() else None
        except (OSError, UnicodeDecodeError):
            return None

    def write_file(self, rel_path: str, content: str) -> WriteResult:
        path = self.resolve(rel_path)
        if path is None or path.is_dir():
            return WriteResult(ok=False, rel_path=rel_path, error="path is outside the writable root, or is a protected file")
        try:
            existed = path.is_file()
            backup = None
            if existed:
                self.backup_dir.mkdir(parents=True, exist_ok=True)
                backup = self.backup_dir / f"{len(list(self.backup_dir.iterdir()))}-{path.name}"
                shutil.copyfile(path, backup)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as error:
            return WriteResult(ok=False, rel_path=rel_path, error=f"{type(error).__name__}: {error}")
        return WriteResult(ok=True, rel_path=rel_path, bytes_written=len(content.encode("utf-8")), created=not existed,
                           backup_path=str(backup) if backup else None)
