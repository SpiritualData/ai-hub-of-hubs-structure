"""Ties each plan piece to the solution it serves, so each piece is done and checked within that solution's own scope.

A planned piece goes to the relevant solution whose name and needs share the most words with it; a solution whose pass says it needs something
and that no piece serves gets a piece of its own, with the worker category of the request's own piece. A tied piece carries ``solution_id``, a
sub-goal whose done-standard is that solution's own target, and, for a worker that takes a brief (file editing, connected systems, agent
sessions), a brief whose context is that solution's generated prompt. A request that concerns no solution keeps its pieces as planned.
Standard library."""
import re
from typing import Any, Dict, List, Mapping, Sequence

BRIEFED = ("file-editing", "connected-system-operations", "delegated-agent-sessions")
WORD = re.compile(r"[a-z0-9]{3,}")


def words(text: str) -> set:
    return set(WORD.findall(str(text).lower()))


def standard_of(finding: Mapping[str, Any]) -> str:
    target = finding.get("target") or {}
    metric = f" ({target['metric_id']}{' ' + str(target['value']) if target.get('value') else ''})" if target.get("metric_id") else ""
    return str(target.get("done_when") or finding.get("needs") or "") + metric


def tied(piece: Mapping[str, Any], finding: Mapping[str, Any], prompt: str) -> Dict[str, Any]:
    out = dict(piece)
    out["solution_id"] = finding["solution_id"]
    out["sub_goal"] = {**dict(piece.get("sub_goal") or {}), "goal": str(piece.get("piece") or ""), "done_standard": standard_of(finding)}
    if str(piece.get("tool") or "") in BRIEFED and piece.get("request") is None:
        brief = "\n\n".join(part for part in (prompt, "## This piece\n" + str(piece.get("piece") or ""),
                                               "## What this solution needs\n" + str(finding.get("needs") or ""),
                                               "## Done when\n" + standard_of(finding)) if part.strip())
        out["request"] = {"goal": str(piece.get("piece") or ""), "brief": brief}
    return out


def tie(pieces: Sequence[Mapping[str, Any]], considered: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """The pieces with each tied to a solution, plus one piece per needing solution no planned piece serves."""
    findings = [f for f in considered.get("findings") or [] if f.get("applies") is not False and str(f.get("needs") or "").strip()]
    if not findings:
        return [dict(p) for p in pieces]
    prompts = dict(considered.get("prompts") or {})
    out: List[Dict[str, Any]] = []
    served = set()
    for piece in pieces:
        if piece.get("solution_id"):
            out.append(dict(piece))
            served.add(piece["solution_id"])
            continue
        text = words(piece.get("piece", ""))
        scored = sorted(((-len(text & words(f"{f.get('name', '')} {f.get('needs', '')}")), n) for n, f in enumerate(findings)))
        best = findings[scored[0][1]] if scored and (scored[0][0] < 0 or len(pieces) == 1) else None
        if best is None or best["solution_id"] in served:
            out.append(dict(piece))
            continue
        served.add(best["solution_id"])
        out.append(tied(piece, best, prompts.get(best["solution_id"], "")))
    tool = str(pieces[0].get("tool") or "") if len(pieces) == 1 else ""
    for finding in findings:
        if finding["solution_id"] not in served:
            piece = {"piece": f"For {finding.get('name') or finding['solution_id']}: {finding['needs']}", "sub_goal": {}, "tool": tool}
            out.append(tied(piece, finding, prompts.get(finding["solution_id"], "")))
    return out
