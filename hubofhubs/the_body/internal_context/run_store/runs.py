"""The run store: where Body keeps the record of each run, apart from the cards the Subconscious recalls from.

A run record says what the system did for a request (the steps of every part, the answer, how many attempts, why it stopped). It is
evidence for Integrity to audit and data for Body to keep, and it is never a card: recalling it as context for the next request would
make the system quote its own past runs instead of what it knows. Kept in memory, and as one JSON file per run in ``folder`` when a folder is
given. Standard library only."""
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


class RunStore:
    """Keeps run records by id, newest last."""

    def __init__(self, folder: str = ""):
        self.folder = Path(folder) if folder else None
        self.rows: Dict[str, Mapping[str, Any]] = {}
        if self.folder is not None:
            self.folder.mkdir(parents=True, exist_ok=True)
            for path in sorted(self.folder.glob("run-*.json")):
                self.rows[path.stem] = json.loads(path.read_text(encoding="utf-8"))

    def add(self, run: Mapping[str, Any]) -> str:
        identifier = f"run-{run.get('id') or len(self.rows) + 1}"
        self.rows[identifier] = dict(run)
        if self.folder is not None:
            (self.folder / f"{identifier}.json").write_text(json.dumps(run, default=str, sort_keys=True), encoding="utf-8")
        return identifier

    def get(self, identifier: str) -> Optional[Mapping[str, Any]]:
        return self.rows.get(identifier)

    def latest(self, limit: int = 10) -> Sequence[Mapping[str, Any]]:
        return list(self.rows.values())[-max(limit, 0):] if limit else []
