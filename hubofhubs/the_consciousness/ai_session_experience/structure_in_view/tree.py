"""Structure In View arm ``event_tree``: pure functions over a session's events and the ESOI records, returning plain data.

The tree follows the agents of the session. An agent works on a solution (``agent-started`` carries it), so the solution of an agent sits under the solution
of its nearest ancestor agent that has one; the run's own solution (``run-started``) is the root. Each solution node says its state, the agents on it and
their latest activity, and stays collapsed: no field of the records is in it. A solution named in ``expanded`` also carries ``detail``: its fields and its
connections with their fields, read from the records. An id the records do not know is shown by the id, marked unknown, and never raises.

``load_tables`` reads the records with ``esoi.read_tree``; every other function takes the tables (``{"solutions": [rows], ...}``), so a case or a
consumer can supply rows from any source. Standard library plus ``esoi``."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import implementation, split_ids
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, AgentStarted, Finished, RunStarted, SessionEvent, Step, event_from_dict)

TABLES = ("solutions", "problems", "ideals", "metrics", "implementations")
ALL = "*"
RUNNING_FIRST = ("running", "failed", "unmet", "stopped", "met", "not_started")


def load_tables(root: Any, results: str = "") -> Dict[str, List[Mapping[str, str]]]:
    """The records under ``root`` as tables, read as one tree, with the recorded results (``results``, default ``esoi/results.csv`` under the root)."""
    from esoi import read_tree
    base = Path(str(root))
    tables: Dict[str, List[Mapping[str, str]]] = {name: list(read_tree(base, name + ".csv")) for name in TABLES}
    path = Path(results) if results else base / "esoi" / "results.csv"
    tables["results"] = list(csv.DictReader(path.open(encoding="utf-8"))) if path.is_file() else []
    return tables


def tables_of(records: Any) -> Optional[Mapping[str, Sequence[Mapping[str, str]]]]:
    """``records`` as tables: a mapping of tables is used as given, a path is read, ``None`` or an unreadable path gives ``None`` (no records)."""
    if records is None or records == "":
        return None
    if isinstance(records, Mapping):
        return records
    try:
        return load_tables(records)
    except Exception:      # noqa: BLE001  a records failure never stops the view; solutions are then shown by id
        return None


def events_of(events: Sequence[Any]) -> List[SessionEvent]:
    """The session events, from objects or dicts; a dict of an unknown type is left out."""
    out: List[SessionEvent] = []
    for item in events or ():
        if isinstance(item, SessionEvent):
            out.append(item)
        elif isinstance(item, Mapping):
            try:
                out.append(event_from_dict(item))
            except (ValueError, TypeError):
                continue
    return out


def row_of(tables: Optional[Mapping[str, Sequence[Mapping[str, str]]]], table: str, key: str, value: str) -> Optional[Mapping[str, str]]:
    for row in (tables or {}).get(table, ()):
        if row.get(key) == value:
            return row
    return None


def latest_result(tables: Mapping[str, Sequence[Mapping[str, str]]], solution: Mapping[str, str]) -> Optional[Dict[str, Any]]:
    """The newest recorded result of the solution's authoritative metric (for the selected arm when there is one, else any arm), or ``None``."""
    metric = row_of(tables, "metrics", "metric_id", solution.get("authoritative_metric_id", "")) or {}
    words = (metric.get("command") or "").split()
    component = words[words.index("run") + 1] if "run" in words and words.index("run") + 1 < len(words) else solution.get("solution_id", "").replace("-", "_")
    rows = [r for r in tables.get("results", ()) if r.get("component") == component]
    chosen = [r for r in rows if r.get("impl") == solution.get("selected")] or rows
    if not chosen:
        return None
    last = sorted(chosen, key=lambda r: r.get("date", ""))[-1]
    return {"component": component, "impl": last.get("impl", ""), "cases": last.get("cases", ""), "passed": last.get("passed", ""),
            "balanced": last.get("balanced", ""), "date": last.get("date", "")}


def milestones_of(text: str) -> List[Dict[str, Any]]:
    from esoi.structure.intent_registry.fields import parse_milestones
    return [{"text": m["text"], "met": bool(m["met"])} for m in parse_milestones(text or "", in_order=True)]


def named(tables: Mapping[str, Sequence[Mapping[str, str]]], table: str, key: str, ids: str, fields: Sequence[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for each in split_ids(ids or ""):
        if each == "none":
            continue
        row = row_of(tables, table, key, each)
        out.append({"id": each, "known": row is not None, **({f: row.get(f, "") for f in fields} if row else {})})
    return out


def detail_of(tables: Optional[Mapping[str, Sequence[Mapping[str, str]]]], solution_id: str) -> Dict[str, Any]:
    """The fields of a solution and its connections with their fields. An unknown solution has none and says so."""
    row = row_of(tables, "solutions", "solution_id", solution_id)
    if row is None or tables is None:
        return {"known": False, "fields": {}, "connections": {"problems": [], "ideals": [], "delegates": []}, "note": "no record for this solution"}
    metric = row_of(tables, "metrics", "metric_id", row.get("authoritative_metric_id", ""))
    selected = row_of(tables, "implementations", "implementation_id", f"{solution_id}:{row.get('selected', '')}")
    fields = {"purpose": row.get("purpose", ""), "approach": row.get("approach", ""), "out_of_scope": row.get("out_of_scope", ""),
              "metric": {"id": row.get("authoritative_metric_id", ""), "name": (metric or {}).get("name", ""), "latest": latest_result(tables, row)},
              "selected": {"id": row.get("selected", ""), "name": (selected or {}).get("name", "")},
              "milestones": milestones_of(row.get("milestones", ""))}
    delegates = []
    for each in named(tables, "solutions", "solution_id", row.get("delegates_to", ""), ("name", "purpose", "approach", "selected")):
        delegates.append(each)
    return {"known": True, "fields": fields,
            "connections": {"problems": named(tables, "problems", "problem_id", row.get("problem_ids", ""), ("name", "problem", "who_has_it", "why_it_matters")),
                            "ideals": named(tables, "ideals", "ideal_id", row.get("ideal_ids", ""), ("name", "principle", "state_description")),
                            "delegates": delegates}}


class Node:
    """One solution in the tree, with the agents working on it."""

    def __init__(self, solution_id: str):
        self.solution, self.agents, self.children = solution_id, [], []


def combined_state(states: Sequence[str]) -> str:
    """One state for a node from its agents' states: running while any runs, else the worst of what ended."""
    present = set(states)
    return next((s for s in RUNNING_FIRST if s in present), "idle")


def build(events: Sequence[SessionEvent]) -> Dict[str, Any]:
    """The skeleton from the events alone: nodes by solution, the agents on each, their state and latest activity, and the agents with no solution."""
    root_solution, finished = "", None
    agents: Dict[str, Dict[str, Any]] = {}
    latest: Dict[str, str] = {}
    for event in events:
        if isinstance(event, RunStarted):
            root_solution = event.solution or root_solution
            finished = None
        elif isinstance(event, AgentStarted):
            agents[event.agent_id] = {"agent_id": event.agent_id, "parent_id": event.parent_id, "task": event.task, "solution": event.solution,
                                      "state": "running", "calls": 0}
        elif isinstance(event, AgentEnded):
            agent = agents.setdefault(event.agent_id, {"agent_id": event.agent_id, "parent_id": MAIN, "task": event.agent_id, "solution": "", "calls": 0})
            agent["state"], agent["calls"] = event.state, event.calls or agent["calls"]
        elif isinstance(event, Step) and event.label:
            latest[event.agent_id] = f"{event.label} ({event.state})"
        elif isinstance(event, Finished):
            finished = event
    return {"root": root_solution, "agents": agents, "latest": latest, "finished": finished}


def solution_of_chain(agents: Mapping[str, Mapping[str, Any]], agent_id: str, root: str) -> str:
    """The solution an agent's work sits under: the nearest ancestor agent with a solution, else the run's solution."""
    seen = set()
    current = agents.get(agent_id, {}).get("parent_id", MAIN)
    while current and current not in seen:
        seen.add(current)
        found = agents.get(current, {}).get("solution", "")
        if found:
            return found
        current = agents.get(current, {}).get("parent_id", "") if current in agents else ""
    return root


def arrange(skeleton: Mapping[str, Any]) -> Dict[str, Any]:
    """The solution nodes (one per solution, the first agent's place decides the parent) as a forest, and the agents with no solution as ``unplaced``."""
    agents, root, finished = skeleton["agents"], skeleton["root"], skeleton["finished"]
    nodes: Dict[str, Node] = {}
    parent_of: Dict[str, str] = {}
    unplaced: List[Dict[str, Any]] = []
    if root:
        nodes[root] = Node(root)
    for agent in agents.values():
        sid = agent["solution"]
        if not sid:
            unplaced.append(agent)
            continue
        node = nodes.setdefault(sid, Node(sid))
        node.agents.append(agent)
        if sid not in parent_of and sid != root:
            above = solution_of_chain(agents, agent["agent_id"], root)
            parent_of[sid] = above if above != sid else root
    for sid, above in parent_of.items():
        if above and above in nodes and above != sid:
            nodes[above].children.append(nodes[sid])
    roots = [n for sid, n in nodes.items() if not (sid in parent_of and parent_of[sid] in nodes and parent_of[sid] != sid)]
    return {"roots": roots, "unplaced": unplaced, "finished": finished, "latest": skeleton["latest"], "run_root": root}


def render_node(node: Node, shape: Mapping[str, Any], tables: Optional[Mapping[str, Sequence[Mapping[str, str]]]], expanded: Sequence[str],
                seen: set) -> Dict[str, Any]:
    row = row_of(tables, "solutions", "solution_id", node.solution)
    states = [a["state"] for a in node.agents]
    if node.solution == shape["run_root"]:
        finished = shape["finished"]
        states.append("running" if finished is None else {"met": "met", "unmet": "unmet", "stopped": "stopped"}.get(finished.outcome, "failed"))
    activity = [shape["latest"][a["agent_id"]] for a in node.agents if a["agent_id"] in shape["latest"]]
    if node.solution == shape["run_root"] and MAIN in shape["latest"]:
        activity.append(shape["latest"][MAIN])
    out: Dict[str, Any] = {"solution": node.solution, "name": (row or {}).get("name") or node.solution, "known": row is not None,
                           "state": combined_state(states),
                           "agents": [{"agent_id": a["agent_id"], "task": a["task"], "state": a["state"], "calls": a["calls"]} for a in node.agents],
                           "activity": activity[-1] if activity else "", "expandable": row is not None, "expanded": False, "children": []}
    seen.add(node.solution)
    if ALL in expanded or node.solution in expanded:
        out["expanded"], out["detail"] = True, detail_of(tables, node.solution)
    out["children"] = [render_node(c, shape, tables, expanded, seen) for c in node.children if c.solution not in seen]
    return out


def structure_view(events: Sequence[Any], records: Any = None, expanded: Sequence[str] = ()) -> Dict[str, Any]:
    """The tree of the solutions the session is working on, collapsed unless named in ``expanded`` (``"*"`` expands every node)."""
    tables = tables_of(records)
    shape = arrange(build(events_of(events)))
    seen: set = set()
    tree = [render_node(n, shape, tables, tuple(expanded or ()), seen) for n in shape["roots"]]
    unknown = sorted({n["solution"] for n in flatten(tree) if not n["known"]})
    return {"tree": tree, "unplaced": [{"agent_id": a["agent_id"], "task": a["task"], "state": a["state"], "parent_id": a["parent_id"]} for a in shape["unplaced"]],
            "unknown": unknown, "expanded": [n["solution"] for n in flatten(tree) if n["expanded"]]}


def flatten(tree: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    out: List[Mapping[str, Any]] = []
    for node in tree:
        out.append(node)
        out.extend(flatten(node["children"]))
    return out


@implementation("structure-in-view", "event_tree")
class EventTree:
    """The agents of the session arranged by the solution each works on, with the records read only for what is expanded."""
    REQUIRES = ()

    def view(self, events: Sequence[Any], records: Any = None, expanded: Sequence[str] = ()) -> Mapping[str, Any]:
        return structure_view(events, records, expanded)
