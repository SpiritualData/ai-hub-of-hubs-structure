"""A consumer's ESOI records as one network: which solutions a text concerns, the scope above each, what relies on each, and each solution's
generated prompt with its knowledge items apart from its stable part.

Everything here is the esoi library's solution consideration (its classifier over the specification index, its prompt formed from a
solution's network of records, and its knowledge items); this module only holds one loaded network per records root so every pass of a
request shares it, and gives the hub one shape whatever esoi version is installed. With an esoi that has no knowledge records yet, the
solution's free-text Knowledge field is split into items, so the selection downstream works the same. Standard library plus ``esoi``."""
from __future__ import annotations

import inspect
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KNOWLEDGE_LINE = "Knowledge: "
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
FIELD_SOURCE = "the solution's knowledge field"
CACHE: Dict[Tuple[str, Tuple[str, ...]], "SolutionNetwork"] = {}
CACHE_LOCK = threading.Lock()


def split_knowledge(sid: str, text: str) -> List[Dict[str, Any]]:
    """The items of a free-text Knowledge field: one per line, or one per sentence when it is one paragraph."""
    lines = [line.strip(" -*\t") for line in str(text or "").splitlines() if line.strip(" -*\t")]
    parts = lines if len(lines) > 1 else [p.strip() for p in SENTENCE.split(lines[0] if lines else "") if p.strip()]
    return [{"id": f"k-{sid}-{n}", "claim": part, "kind": "", "source": FIELD_SOURCE, "source_kind": "other", "grade": "", "solution_ids": [sid],
             "status": "active", "recorded": "", "expiration": "", "rank": 0.0} for n, part in enumerate(parts, 1)]


class SolutionNetwork:
    """The records under ``root`` (a folder with an ``esoi.toml``), loaded once. ``extra`` names finding or candidate files that are not
    declared in the records configuration."""

    def __init__(self, root: Any, extra: Sequence[str] = (), stale: bool = False):
        from esoi.structure.intent_registry import config as config_module
        from esoi.understanding.solution_consideration import fan_out, solution_prompt
        from esoi.understanding.spec_search import spec_index
        self.root = str(root)
        self.extra = tuple(extra)
        self.prompts, self.fan_out = solution_prompt, fan_out
        self.config = config_module.load(Path(self.root))
        self.net = solution_prompt.load(self.config, extra=list(extra), stale=stale)
        self.index = spec_index.build(self.config)
        self.budget = solution_prompt.budget_of(self.config)
        self.has_knowledge = "knowledge" in inspect.signature(solution_prompt.prompt).parameters

    @classmethod
    def from_rows(cls, tables: Mapping[str, Sequence[Mapping[str, str]]], name: str = "rows") -> "SolutionNetwork":
        """The network of records any source supplies as rows (``{table: [row, ...]}``: intents, problems, ideals, solutions,
        implementations, metrics, results, knowledge, findings, evidence), with no folder: the esoi library's ``from_rows`` and
        ``build_from_rows``. ``name`` stands for the root in what the arms return."""
        from esoi.understanding.solution_consideration import fan_out, solution_prompt
        from esoi.understanding.spec_search import spec_index
        made = cls.__new__(cls)
        made.root, made.extra = name, ()
        made.prompts, made.fan_out = solution_prompt, fan_out
        made.net = solution_prompt.from_rows(tables)
        made.config = made.net.config
        made.index = spec_index.build_from_rows({k: list(v) for k, v in tables.items()})
        made.budget = solution_prompt.DEFAULT_BUDGET
        made.has_knowledge = True
        return made

    def has(self, sid: str) -> bool:
        return sid in self.net.solutions

    def name(self, sid: str) -> str:
        return str(self.net.solutions.get(sid, {}).get("name") or sid)

    def row(self, sid: str) -> Mapping[str, str]:
        return self.net.solutions.get(sid, {})

    def classify(self, text: str, limit: int = 5, arm: str = "") -> List[Dict[str, Any]]:
        """The solutions a text concerns, best first, without their parents (the chain is said apart). ``arm`` names an esoi relevance arm;
        empty is the one esoi's records select, and when that selection cannot be resolved from where it runs the library's links arm is used."""
        try:
            return list(self.fan_out.classify(self.net, self.index, text, limit, arm, parents=False))
        except ValueError:      # esoi's SelectionError: the records name an arm the library does not declare
            if arm:
                raise
            return list(self.fan_out.classify(self.net, self.index, text, limit, self.fallback_arm(), parents=False))

    @staticmethod
    def fallback_arm() -> str:
        """The library's arm that follows each hit's links (its records' selection when it names one), else its first arm."""
        from esoi.understanding.solution_relevance import relevance
        names = list(relevance.ARMS)
        return next((n for n in names if "links" in n), names[0])

    def parent(self, sid: str) -> str:
        return self.prompts.parent_of(self.net, sid)

    def chain(self, sid: str, depth: int = 3) -> List[str]:
        """The scopes above ``sid``, nearest first, at most ``depth`` of them."""
        out: List[str] = []
        current = sid
        while len(out) < depth:
            current = self.parent(current)
            if not current or current in out or current == sid:
                break
            out.append(current)
        return out

    def children(self, sid: str) -> List[str]:
        return list(self.prompts.children_of(self.net, sid))

    def dependents(self, sid: str) -> Dict[str, str]:
        """``{solution id: what relies on sid}``, without the scopes above it (those get their own pass)."""
        above = set(self.chain(sid, 10))
        return {d: how for d, how in self.prompts.dependents_of(self.net, sid).items() if d not in above}

    def prompt(self, sid: str, task: str = "", role: str = "solution", budget: int = 0) -> Dict[str, Any]:
        """The stable part of the solution's generated prompt as ``text``, with ``knowledge`` (active items) and ``knowledge_inactive`` apart."""
        size = budget or self.budget
        if self.has_knowledge:
            made = dict(self.prompts.prompt(self.net, sid, task, size, role, knowledge="candidates"))
            made.setdefault("knowledge", [])
            made.setdefault("knowledge_inactive", [])
            return made
        made = dict(self.prompts.prompt(self.net, sid, task, size, role))
        lines = made["text"].splitlines()
        made["text"] = "\n".join(line for line in lines if not line.startswith(KNOWLEDGE_LINE))
        made["knowledge"] = split_knowledge(sid, self.row(sid).get("knowledge", ""))
        made["knowledge_inactive"] = []
        return made


def network_of(records: Any, extra: Sequence[str] = (), fresh: bool = False) -> Any:
    """The network for ``records``: an object that already answers ``classify`` and ``prompt`` is used as it is; a records root is loaded once
    and kept, and loaded again when ``fresh`` (after a write to its records)."""
    if hasattr(records, "classify") and hasattr(records, "prompt"):
        return records
    key = (str(Path(str(records)).resolve()), tuple(extra))
    with CACHE_LOCK:
        if fresh or key not in CACHE:
            CACHE[key] = SolutionNetwork(key[0], extra)
        return CACHE[key]


def forget(records: Optional[Any] = None) -> None:
    """Drops the kept network of ``records`` (every kept network when None), so the next request reads the records again."""
    with CACHE_LOCK:
        if records is None:
            CACHE.clear()
            return
        root = str(Path(str(records)).resolve())
        for key in [k for k in CACHE if k[0] == root]:
            del CACHE[key]
