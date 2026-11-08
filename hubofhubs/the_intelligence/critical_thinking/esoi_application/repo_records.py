"""A records location for ESOI Application over a records root the esoi library reads (a folder with an ``esoi.toml``).

It reads the solutions and the knowledge items through the library, and it writes one thing itself: a knowledge item, through the library's own
writer (``esoi.understanding.solution_consideration.knowledge.add``, ensure-one, sourced), so the records' checks see one shape. Every other edit
(a field of a solution, a new implementation row) is held as ``proposed`` for a person or the records tool, never written here. After a write the
kept network of that root is dropped, so the next request's prompts carry the new item. Standard library plus ``esoi``."""
from pathlib import Path
from typing import Any, Dict, Mapping

from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import forget, network_of


class RepoRecords:
    """The records under ``root``; ``writes_knowledge`` False holds every edit as proposed (a read-only location)."""

    def __init__(self, root: Any, writes_knowledge: bool = True):
        self.root, self.writes_knowledge = str(root), writes_knowledge

    def read(self, subject: str = "") -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        network = network_of(self.root)
        tables: Dict[str, Dict[str, Dict[str, Any]]] = {"solutions": {sid: dict(row) for sid, row in network.net.solutions.items()}, "knowledge": {}}
        try:
            from esoi.understanding.solution_consideration import knowledge
            tables["knowledge"] = {str(item.get("id")): dict(item) for item in knowledge.all_items(network.config)}
        except ImportError:
            pass
        return tables

    def apply(self, edit: Mapping[str, Any]) -> Mapping[str, Any]:
        if edit.get("op") != "add" or edit.get("table") != "knowledge":
            return {"status": "proposed", "reason": "only a knowledge item is written here; this edit waits for a person or the records tool"}
        if not self.writes_knowledge:
            return {"status": "proposed", "reason": "this records location is read-only; the knowledge item waits for a person"}
        try:
            from esoi.structure.intent_registry import config as config_module
            from esoi.understanding.solution_consideration import knowledge
        except ImportError:
            return {"status": "proposed", "reason": "the installed esoi has no knowledge records yet; the item waits"}
        fields = dict(edit.get("fields") or {})
        ids = [s for s in str(fields.get("solution_ids") or "").split(";") if s]
        item = {"claim": fields.get("claim", ""), "kind": fields.get("kind", "lesson"), "source": fields.get("source", ""), "solution_ids": ids,
                "status": fields.get("status", "active")}
        knowledge_id, created = knowledge.add(config_module.load(Path(self.root)), item)
        forget(self.root)
        return {"status": "applied" if created else "unchanged", "target": knowledge_id}
