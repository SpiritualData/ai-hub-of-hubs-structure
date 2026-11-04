"""The fixed selector of the component: Quest AI Runner's keyword IDF card store at the pinned commit, confidence gate off.

Every builder is scored through the same selector, so only the cards differ. The selector ranks the cards for a task and shows the
best ten; the view is the picked cards in rank order, each card's files in the order the builder gave them (production renders a
card's files as they are listed, with no per-query reordering). The store is QAR's ``FileContextStore`` imported from the pinned
archive of the corpus (``corpus.selector_path``), never from a working tree.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

VIEW_CARDS = 10


def store_class(selector_path: Path):
    """``FileContextStore`` of the pinned archive; refuses a ``quest_ai_runner`` imported from anywhere else."""
    here = str(selector_path)
    if here not in sys.path:
        sys.path.insert(0, here)
    from quest_ai_runner.adapters.file_context_store import FileContextStore
    where = Path(sys.modules[FileContextStore.__module__].__file__).resolve()
    if selector_path.resolve() not in where.parents:
        raise RuntimeError(f"quest_ai_runner was already imported from {where}, not from the pinned archive {selector_path}")
    return FileContextStore


def normalise(card: Mapping[str, Any]) -> Dict[str, Any]:
    """A builder's card as the store's record: file entries are mappings with a path and symbols."""
    record = dict(card)
    record["files"] = [dict(f) if isinstance(f, Mapping) else dict(path=f, symbols=[]) for f in card.get("files", [])]
    record.setdefault("keywords", [])
    record.setdefault("summary", "")
    record.setdefault("description", "")
    record.setdefault("weight", 1.0)
    return record


class Selector:
    """A store holding exactly the cards given; ``view(task)`` is the list of file paths the task is shown."""

    def __init__(self, cards, corpus):
        records = {}
        for card in cards:
            record = normalise(card)
            if record["id"] in records:
                raise ValueError(f"two cards share the id {record['id']!r}")
            records[record["id"]] = record
        self.records = records
        self.store = store_class(corpus.selector_path)(tempfile.mkdtemp(prefix="cards_from_files_"), repo_root=str(corpus.root),
                                                       auto_bootstrap=False, confidence_threshold=0.0, max_cards_in_view=VIEW_CARDS)
        for card_id, record in records.items():
            self.store._own_repo.write(card_id, record)
        self.store._cache_dirty = True

    def view(self, task: str) -> List[str]:
        picked = self.store.assemble(task).card_ids
        return [entry["path"] for card_id in picked for entry in self.records[card_id]["files"]]
