"""What a request's consideration and checks leave in the records, and whether the checked pieces still combine.

``proposals_of`` turns the passes' findings and the piece checks into ESOI Application changes, each sourced: a knowledge item a pass proposed
(``record_add`` to the ``knowledge`` table), a checked piece's result as an evidence item on its solution, and a candidate a pass named as a
not-built implementation. ``combined_check`` reads the parent passes: a scope whose pass found an effect on how its children combine is met only
when every checked piece under it is met, and a dependent whose pass says what it relies on no longer holds makes the whole unmet.
Standard library."""
import re
from typing import Any, Dict, List, Mapping, Sequence

SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str, size: int = 48) -> str:
    return SLUG.sub("-", str(text).lower()).strip("-")[:size].strip("-")


def knowledge_change(sid: str, claim: str, kind: str, source: str) -> Dict[str, Any]:
    return {"kind": "record_add", "table": "knowledge", "key": f"{sid}:{slug(claim)}",
            "fields": {"claim": claim, "kind": kind or "lesson", "source": source, "solution_ids": sid, "status": "active"}}


def proposals_of(considered: Mapping[str, Any], checked: Mapping[str, Any], today: str = "") -> List[Dict[str, Any]]:
    """The changes to propose, in order: knowledge items from the passes, results of the checked pieces, then candidates."""
    when = f" on {today}" if today else ""
    out: List[Dict[str, Any]] = []
    for finding in considered.get("findings") or []:
        sid = finding["solution_id"]
        for item in finding.get("knowledge") or []:
            source = f"the consideration pass of {sid}{when}" + (f", from {item['source']}" if item.get("source") else "")
            out.append(knowledge_change(sid, str(item["claim"]).strip(), str(item.get("kind") or "lesson"), source))
    for piece in checked.get("pieces") or []:
        if piece.get("met") is None:
            continue
        verdict = "met" if piece["met"] else "did not meet"
        claim = (f"A piece of work for this solution {verdict} its target{when}"
                 + (f" ({piece['metric_id']}{' ' + piece['value'] if piece.get('value') else ''})" if piece.get("metric_id") else "")
                 + f": {piece.get('done_standard') or piece.get('piece')}" + (f". Why: {piece['reason']}" if piece.get("reason") else ""))
        out.append(knowledge_change(piece["solution_id"], claim, "evidence", f"Goal Completion's check of the piece{when}"))
    for finding in considered.get("findings") or []:
        for name in finding.get("candidates") or []:
            sid = finding["solution_id"]
            out.append({"kind": "record_add", "table": "implementations", "key": f"{sid}:{slug(name)}",
                        "fields": {"solution_id": sid, "name": str(name), "description": f"Not built. Named by a request{when} and proposed by this solution's consideration pass."}})
    return out


def descendants(parent: str, parents: Sequence[Mapping[str, Any]]) -> List[str]:
    """Every solution under ``parent`` that a parent pass names, through the levels between."""
    children = {p["solution_id"]: list(p.get("children") or []) for p in parents}
    out, todo = [], list(children.get(parent, []))
    while todo:
        sid = todo.pop()
        if sid not in out:
            out.append(sid)
            todo += children.get(sid, [])
    return out


def combined_check(pieces: Sequence[Mapping[str, Any]], considered: Mapping[str, Any]) -> Dict[str, Any]:
    """Whether the checked pieces still combine: ``met`` and the ``reasons`` it rests on."""
    reasons: List[str] = []
    by_solution: Dict[str, List[Mapping[str, Any]]] = {}
    for piece in pieces:
        by_solution.setdefault(piece["solution_id"], []).append(piece)
    parents = list(considered.get("parents") or [])
    for scope in parents:
        if scope.get("combination_effect") is not True:
            continue
        under = [p for sid in descendants(scope["solution_id"], parents) for p in by_solution.get(sid, [])]
        unmet = [p["solution_id"] for p in under if p.get("met") is False]
        if unmet:
            reasons.append(f"{scope.get('name') or scope['solution_id']} combines its children differently after this change and "
                           f"{', '.join(sorted(set(unmet)))} did not meet its target")
        if scope.get("metric_update"):
            reasons.append(f"{scope.get('name') or scope['solution_id']} needs its metric or combination updated: {scope['metric_update']}")
    for dependent in considered.get("dependents") or []:
        if dependent.get("still_holds") is False:
            reasons.append(f"{dependent.get('name') or dependent['solution_id']} no longer gets what it relies on: {dependent.get('why') or ''}".strip())
    blocking = [r for r in reasons if "did not meet" in r or "no longer gets" in r]
    return {"met": not blocking, "reasons": reasons}
