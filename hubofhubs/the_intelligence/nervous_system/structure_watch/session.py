"""The structure watch of ``ahohs work``: read the records, ask Proactivity whether the watch is due, run it once, say what it found in a few lines and its spend in one.

``structure_of`` reads the records of a folder as one tree (``esoi.read_tree``) with the recorded results and the run's own summary; ``work_hook`` is what the terminal calls at the
end of each run (``moment`` end_of_run) and, with ``start``, when a session opens. The watch is off with ``off=True`` (``--structure-watch off``). Standard library plus the hub and ``esoi``."""
import csv
import time
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional

from hubofhubs.the_intelligence.nervous_system.structure_watch.watch import BestTierCall, FindingsOnly, KIND, OUTPUT_TOKENS
from hubofhubs.the_intelligence.proactivity import standing

TABLES = ("solutions", "implementations", "metrics", "experiments", "investigations")


def structure_of(root: Any, runs: Optional[List[Mapping[str, Any]]] = None, now: str = "") -> Mapping[str, Any]:
    from esoi import read_tree
    base = Path(str(root))
    tables = {name: list(read_tree(base, name + ".csv")) for name in TABLES}
    path = base / "esoi" / "results.csv"
    results = list(csv.DictReader(path.open(encoding="utf-8"))) if path.is_file() else []
    return {"intent": base.name, "tables": tables, "results": results, "runs": list(runs or ()), "now": now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def solutions_of_files(structure: Mapping[str, Any], files: List[str]) -> List[str]:
    """The solutions whose implementations are in the changed files (by the ``filepath`` of the implementation records)."""
    return sorted({str(r.get("solution_id")) for r in structure["tables"]["implementations"] if any(str(r.get("filepath") or "") == f or f.endswith(str(r.get("filepath") or "~")) for f in files)})


def lines_of(result: Mapping[str, Any]) -> List[str]:
    """What to say after a run: nothing when the watch did not run for a reason the person need not see, the items when it raised some, and one spend line when it made a call."""
    out = []
    for item in result.get("items") or ():
        route = "proposal for you" if item.get("route") == "proposal" else ("applied by the AI, recorded" if item.get("route") == "applied" else "noted")
        out.append(f"structure ({item['severity']}, {route}): {item['what']} Why now: {item['why_now']} Next: {item.get('step_text') or item['step']}")
    if result.get("called"):
        out.append(f"structure watch: 1 call on the {result['tier']} tier, {result['tokens_in']} tokens in and {result['tokens_out']} out (cap {OUTPUT_TOKENS}), {len(result.get('items') or ())} item(s)"
                   + (f"; {result['tier_note']}" if result.get("tier_note") else ""))
    return out


def work_hook(records: Any, store: Any, ask: Optional[Callable[..., Any]] = None, judge: Optional[Callable[..., Mapping[str, Any]]] = None,
              applier: Optional[Callable[..., Mapping[str, Any]]] = None, off: bool = False, ceilings: Optional[Mapping[str, Any]] = None) -> Callable[..., List[str]]:
    """``hook(files, summary, moment="end_of_run")`` for the terminal: the lines to say, empty when the watch is not due."""
    def hook(files: List[str], summary: str = "", moment: str = standing.END_OF_RUN) -> List[str]:
        if records is None or off:
            return []
        try:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            last = next((r for r in reversed(list(store.latest(50))) if r.get("kind") == KIND), {})
            probe = structure_of(records, now=now)
            changed = now if files else ""       # a run that changed files is the event; a session start with no change has none
            if not standing.due(moment, now, last.get("time"), changed, off)["due"]:
                return []
            run = {"at": now, "summary": summary, "solutions": solutions_of_files(probe, files)}
            arm = (BestTierCall if ask is not None else FindingsOnly)(ask=ask, store=store, judge=judge, applier=applier, ceilings=ceilings)
            return lines_of(arm.watch(dict(probe, runs=[run]), now))
        except Exception as error:      # noqa: BLE001 a watch never ends a run badly
            return [f"structure watch did not run: {type(error).__name__}"]
    return hook
