"""Intake Sources (Body): the adapters that say where a system's requests come from, and read them. A source is declared by the system
(a chat, a task queue, a place meeting action items are written); Body defines the adapter, Consciousness's Request Intake uses it.

``folder_queue`` is the default: a folder of queued requests, one JSON file per request with ``text`` and optionally ``person`` and
``source``, taken oldest first and removed once taken so a request is handed over once. A system declares its own adapter (a chat, a task
list) as another arm. Standard library plus the hub and ``esoi``."""
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation


@implementation("intake-sources", "folder_queue")
class FolderQueue:
    """Requests queued as JSON files in one folder; taking a request removes its file."""
    REQUIRES = ()     # a folder on disk, given to the constructor

    def __init__(self, folder: str = ".hubofhubs/requests"):
        self.folder = Path(folder)

    def sources(self) -> Sequence[Mapping[str, Any]]:
        return [{"kind": "queued tasks", "where": str(self.folder), "default": True}]

    def pull(self, source: str = "", limit: int = 10) -> Sequence[Mapping[str, Any]]:
        taken: List[Dict[str, Any]] = []
        for path in sorted(self.folder.glob("*.json"), key=lambda p: (p.stat().st_mtime, p.name))[:limit]:
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(row, dict) or not str(row.get("text", "")).strip():
                continue
            taken.append({"text": str(row["text"]).strip(), "person": str(row.get("person", "")), "source": str(row.get("source") or path.stem)})
            path.unlink()
        return taken
