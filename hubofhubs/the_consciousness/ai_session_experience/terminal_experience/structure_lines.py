"""The structure view as terminal lines: one line per solution while collapsed, its fields and connections only for a solution that is expanded.

Input is the plain data Structure In View returns (``tree`` of solution nodes); output is plain lines, ASCII only, so a line REPL, a live screen or a log
shows it the same. A collapsed node is ``+ Name (id) [state] agents, latest activity``; an expanded one is ``-`` and is followed by its fields and connections,
indented. Standard library only."""
from __future__ import annotations

from typing import Any, List, Mapping, Sequence

from hubofhubs.the_consciousness.ai_session_experience.session_events import short


def agents_text(node: Mapping[str, Any]) -> str:
    count = len(node.get("agents") or ())
    return f"{count} agent{'' if count == 1 else 's'}" if count else "no agent"


def detail_lines(detail: Mapping[str, Any], indent: str, width: int) -> List[str]:
    """The fields and the connections of one expanded solution."""
    if not detail.get("known"):
        return [f"{indent}{detail.get('note') or 'no record for this solution'}"]
    fields, links = detail.get("fields") or {}, detail.get("connections") or {}
    out: List[str] = []
    for label, key in (("purpose", "purpose"), ("approach", "approach")):
        if fields.get(key):
            out.append(f"{indent}{label}: {short(fields[key], width)}")
    metric = fields.get("metric") or {}
    if metric.get("id"):
        latest = metric.get("latest") or {}
        value = f"{latest.get('balanced') or latest.get('passed', '')} ({latest.get('impl', '')}, {latest.get('date', '')})" if latest else "not measured"
        out.append(f"{indent}metric: {metric.get('name') or metric['id']}: {value}")
    if (fields.get("selected") or {}).get("id"):
        out.append(f"{indent}selected: {fields['selected'].get('name') or fields['selected']['id']}")
    for number, milestone in enumerate(fields.get("milestones") or (), 1):
        out.append(f"{indent}milestone {number} [{'met' if milestone.get('met') else 'open'}]: {short(milestone.get('text', ''), width)}")
    for problem in links.get("problems") or ():
        out.append(f"{indent}problem {problem.get('name') or problem['id']}: {short(problem.get('problem', ''), width)}")
    for ideal in links.get("ideals") or ():
        out.append(f"{indent}ideal {ideal.get('name') or ideal['id']}: {short(ideal.get('principle', ''), width)}")
    for delegate in links.get("delegates") or ():
        out.append(f"{indent}delegates to {delegate.get('name') or delegate['id']}: {short(delegate.get('purpose', ''), width)}")
    return out


def structure_lines(view: Mapping[str, Any], width: int = 100, selected: str = "") -> List[str]:
    """The lines of a structure view, collapsed unless a node carries ``detail``. With ``selected`` (a solution id) that row starts with ``>`` and the others with a space."""
    lines: List[str] = []

    def walk(nodes: Sequence[Mapping[str, Any]], depth: int) -> None:
        for node in nodes:
            pad = "  " * depth
            mark = "-" if node.get("expanded") else ("+" if node.get("expandable") else " ")
            activity = f", {short(node['activity'], 40)}" if node.get("activity") else ""
            lead = ("> " if node.get("solution") == selected else "  ") if selected else ""
            lines.append(f"{lead}{pad}{mark} {node.get('name')} ({node.get('solution')}) [{node.get('state')}] {agents_text(node)}{activity}")
            if node.get("detail") is not None:
                lines.extend(detail_lines(node["detail"], pad + "    ", max(width - len(pad) - 24, 30)))
            walk(node.get("children") or (), depth + 1)
    walk(view.get("tree") or (), 0)
    for agent in view.get("unplaced") or ():
        lines.append(f"{'  ' if selected else ''}  helper {short(agent.get('task', ''), 40)} [{agent.get('state')}] (no solution)")
    return lines
