"""The dependency graph of the records: needs read from typed constructor parameters, checked against ``uses_solution_ids``.

Pure functions over record rows (dicts). ``declared_needs`` loads each implementation through the hub's safe-loading path
and reads its parameters; ``problems`` checks the rows against those needs. ``scripts/sync_uses.py`` and the hub tests call both.
"""
import csv
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Set

from . import resolution
from .needs import needs_of


def read_rows(folder: Path, name: str) -> List[Dict[str, str]]:
    with open(Path(folder) / name, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split(cell: str) -> List[str]:
    return [x.strip() for x in (cell or "").split(";") if x.strip()]


def declared_needs(implementations: Sequence[Mapping[str, str]]) -> Dict[str, Set[str]]:
    """``{implementation_id: {seat ids it needs}}`` read from the constructor parameters of each declared implementation."""
    found = {}
    for row in implementations:
        sid, _, name = row["implementation_id"].partition(":")
        found[row["implementation_id"]] = set(needs_of(resolution.load(sid, name)).values())
    return found


def cycle_of(edges: Mapping[str, Set[str]]) -> List[str]:
    """One dependency cycle in ``{seat: {seats it needs}}`` as a list ending where it began, or []."""
    state: Dict[str, int] = {}
    stack: List[str] = []

    def visit(node: str) -> List[str]:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if state.get(nxt) is None:
                ring = visit(nxt)
                if ring:
                    return ring
        stack.pop()
        state[node] = 2
        return []

    for node in sorted(edges):
        if state.get(node) is None:
            ring = visit(node)
            if ring:
                return ring
    return []


def problems(solutions: Sequence[Mapping[str, str]], implementations: Sequence[Mapping[str, str]],
             needs: Mapping[str, Set[str]]) -> List[str]:
    """Every way the records and the declared needs disagree. Empty means the graph is sound."""
    bad: List[str] = []
    seats = {s["solution_id"]: s for s in solutions}
    tags = {sid: set(split(s.get("tags", ""))) for sid, s in seats.items()}
    for row in implementations:
        iid = row["implementation_id"]
        recorded = set(split(row.get("uses_solution_ids", "")))
        if iid in needs and recorded != needs[iid]:
            bad.append(f"{iid}: uses_solution_ids is {sorted(recorded) or 'empty'} but its constructor parameters need "
                       f"{sorted(needs[iid]) or 'nothing'} (run scripts/sync_uses.py)")
        for need in sorted(needs.get(iid, set())):
            if need not in seats:
                bad.append(f"{iid}: needs {need}, which is no solution in the records")
            elif not seats[need].get("selected", "").strip() and "consumer-provided" not in tags[need]:
                kind = "external seat" if "external" in tags[need] else "seat"
                bad.append(f"{iid}: needs {need}: the {kind} has no default arm and is not tagged consumer-provided")
    for sid, tag in tags.items():
        if "consumer-provided" in tag and seats[sid].get("selected", "").strip():
            bad.append(f"{sid}: tagged consumer-provided but has a default arm ({seats[sid]['selected']})")
    default = {sid: s.get("selected", "").strip() for sid, s in seats.items()}
    edges: Dict[str, Set[str]] = {}
    for row in implementations:
        sid = row["solution_id"]
        if default.get(sid) and row["implementation_id"].partition(":")[2] == default[sid]:
            edges.setdefault(sid, set()).update(needs.get(row["implementation_id"], set()))
    ring = cycle_of(edges)
    if ring:
        bad.append("default arms form a cycle: " + " -> ".join(ring))
    return bad
