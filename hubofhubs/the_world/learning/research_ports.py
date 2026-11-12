"""The three places recorded research reaches, as ports a consumer supplies and the hub's own folder defaults.

``recorded_research`` (Learning's arm that records and reuses research) never knows where a consumer keeps its structure. It is handed:

- an ``InvestigationStore``: where investigations live (``related`` reads the earlier ones that bear on given solutions, ``items`` reads one's kept findings,
  ``write`` records one and answers its id; writing the same id again updates it in place);
- a ``KnowledgeSink``: where a kept finding becomes a knowledge item of the solution it informs (``add``: ensure-one, never overwriting what a person wrote;
  it answers ``applied``, ``unchanged`` or ``proposed``, the last when the location holds the change for a person);
- a ``ContextSink``: where one context item per investigation goes so retrieval can surface it for related questions (``put``; a ``scope`` list fences it).

The defaults keep all three in the hub's own folders (``FolderStore`` over ``investigations.csv``, ``FolderKnowledge`` over the ``knowledge.csv`` of the solution's
folder, no context sink). Standard library plus the hub; no model call, no network.
"""
import csv
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import typing

from esoi import split_ids

from hubofhubs.the_world.learning import investigation_record as inv, investigation_store
from hubofhubs.the_world.learning.research_freshness_reader import registry

KNOWLEDGE_COLUMNS = ["knowledge_id", "claim", "kind", "source", "solution_ids", "status", "status_by", "recorded", "expiration", "investigation_id"]
SCOPE = "scope:"      # a link ``scope:<tag>`` fences an investigation: only a request carrying one of its tags sees it


class InvestigationStore(typing.Protocol):
    def related(self, solution_ids: Sequence[str], scope: Sequence[str] = (), today: str = "") -> List[Dict[str, str]]: ...

    def items(self, investigation_id: str) -> List[Dict[str, str]]: ...

    def write(self, spec: Mapping[str, Any]) -> str: ...


class KnowledgeSink(typing.Protocol):
    def add(self, solution_ids: Sequence[str], claim: str, source: str, knowledge_id: str, investigation_id: str, kind: str = "evidence", recorded: str = "") -> Mapping[str, Any]: ...


class ContextSink(typing.Protocol):
    def put(self, item: Mapping[str, Any]) -> None: ...


def scope_of(links: Sequence[str]) -> List[str]:
    """The fence tags in a link list (``scope:<tag>``), in order."""
    return [link[len(SCOPE):] for link in links if link.startswith(SCOPE)]


def visible(row: Mapping[str, str], scope: Sequence[str]) -> bool:
    """An investigation fenced by scope tags is seen only by a request carrying one of them; one with no tag is seen by every request."""
    tags = scope_of(split_ids(row.get("links", "")))
    return not tags or bool(set(tags) & set(scope))


class FolderStore:
    """The hub's own folder store: the two investigation files under ``root`` (default: beside the registry)."""

    def __init__(self, root: Any = None):
        self.root = root

    @property
    def folder(self) -> Path:
        return Path(self.root) / "hubofhubs" / "registry" if self.root else Path(registry.DATA)

    def related(self, solution_ids: Sequence[str], scope: Sequence[str] = (), today: str = "") -> List[Dict[str, str]]:
        seen, out = set(), []
        for solution_id in solution_ids:
            for row in investigation_store.investigations_for(solution_id, True, today, self.root):
                if row["investigation_id"] not in seen and visible(row, scope):
                    seen.add(row["investigation_id"])
                    out.append(row)
        return sorted(out, key=lambda r: r.get("done_on") or "", reverse=True)

    def items(self, investigation_id: str) -> List[Dict[str, str]]:
        return [{c: i.get(c, "") for c in inv.ITEM_COLUMNS} for i in investigation_store.rows(self.root, investigation_store.ITEMS) if i.get("investigation_id") == investigation_id]

    def write(self, spec: Mapping[str, Any]) -> str:
        return investigation_store.record_investigation(spec, self.folder, allow_gaps=True)["investigation_id"]


def norm(text: str) -> str:
    return " ".join((text or "").lower().split())


class FolderKnowledge:
    """A knowledge item in the ``knowledge.csv`` of the folder that holds the (first) solution, written once: a claim already there for that solution, by anyone,
    is left as it is (``unchanged``). A solution with no folder in the records is held as ``proposed``."""

    def __init__(self, root: Any = None):
        self.root = root

    def folder_of(self, solution_id: str) -> Optional[Path]:
        if self.root:
            for path in sorted((Path(self.root) / "hubofhubs").rglob("solutions.csv")):
                if any(r.get("solution_id") == solution_id for r in csv.DictReader(open(path, newline=""))):
                    return path.parent
            return None
        return investigation_store.solution_dir(solution_id)

    def add(self, solution_ids: Sequence[str], claim: str, source: str, knowledge_id: str, investigation_id: str, kind: str = "evidence", recorded: str = "") -> Mapping[str, Any]:
        folder = self.folder_of(solution_ids[0]) if solution_ids else None
        if folder is None:
            return {"status": "proposed", "reason": "the solution has no records folder here, so the item waits for a person"}
        path = folder / "knowledge.csv"
        with investigation_store.locked(folder):
            held = list(csv.DictReader(open(path, newline=""))) if path.exists() else []
            if any(r.get("knowledge_id") == knowledge_id or (norm(r.get("claim", "")) == norm(claim) and solution_ids[0] in split_ids(r.get("solution_ids", ""))) for r in held):
                return {"status": "unchanged", "target": knowledge_id}
            held.append({"knowledge_id": knowledge_id, "claim": claim, "kind": kind, "source": source, "solution_ids": ";".join(solution_ids), "status": "active",
                         "recorded": recorded, "investigation_id": investigation_id})
            investigation_store.write_table(path, KNOWLEDGE_COLUMNS, held)
        return {"status": "applied", "target": knowledge_id}
