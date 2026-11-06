"""A context assembler that reads a folder's files through the ``context-retriever`` seat: the units that answer the task, within a token budget."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


from hubofhubs.the_body.internal_context.interface import AssembledContext
from hubofhubs.the_intelligence.subconscious.context_retriever.interface import ContextRetrieval

TEXT_EXTENSIONS = {".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json", ".sh", ".ts", ".tsx", ".js", ".go", ".rs", ".java"}
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".mypy_cache", ".pytest_cache"}
MAX_FILE_BYTES = 256 * 1024


def read_files(root: str) -> Dict[str, str]:
    """The text files under ``root`` as ``{relative path: text}``; an unreadable or oversized file is left out."""
    base = Path(root)
    found: Dict[str, str] = {}
    for folder, names, files in os.walk(base):
        names[:] = sorted(n for n in names if n not in SKIP)
        for name in sorted(files):
            path = Path(folder) / name
            if path.suffix in TEXT_EXTENSIONS and path.stat().st_size <= MAX_FILE_BYTES:
                try:
                    found[str(path.relative_to(base))] = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
    return found


class FileRetrievalAssembler:
    """Assembles the context for a task from the files under ``root``, picked by whichever ``context-retriever`` arm the hub selected. It
    renders each returned unit under its file and first line, and returns an empty view when the arm judges the task needs no context."""
    REQUIRES = ()     # the context-retriever seat supplies the ranking; this reads the folder

    def __init__(self, retriever: ContextRetrieval, root: str = "", budget_tokens: int = 4000) -> None:
        self.retriever, self.root, self.budget_tokens = retriever, root, budget_tokens
        self.files: Optional[Dict[str, str]] = None

    def assemble(self, task_text: str, *, meta: Optional[Dict[str, Any]] = None, on_event: Optional[Any] = None) -> AssembledContext:
        try:
            if self.files is None:
                self.files = read_files(self.root) if self.root else {}
            hits = list(self.retriever.retrieve(task_text, self.files, self.budget_tokens)) if self.files else []
            sections = [f"### {h.file} (line {h.start})\n{h.text}" for h in hits]
            return AssembledContext(context_view="\n\n".join(sections), card_ids=[h.id for h in hits],
                                    sources=[{"adapter": "retrieval", "label": "retrieved files", "items": [h.id for h in hits]}])
        except Exception:  # noqa: BLE001  an assembler never raises: no context is the safe answer
            return AssembledContext()

    def record(self, task_text: str, outcome: Dict[str, Any]) -> None:
        return None
