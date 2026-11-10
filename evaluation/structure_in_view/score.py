"""Scores a Structure In View arm: is the tree of solutions right, collapsed by default, complete when opened, and safe for an unknown solution?

The cases (``build_cases.py``) give invented events and invented records (``fixture.py``); an arm returns the tree and the score reads from it what the case names:
the outline of the hierarchy, the agents of a solution, paths into one node, the nodes that carry detail and whether any text of the records' fields is in the data
while collapsed. A case passes when the read values equal the expected ones written by hand. One number: the share of cases right, balanced with cost and time
by ``[balance.structure_in_view]``. No model call, no network. What it cannot see: whether a real session's tree is clear or the right level of detail."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from offline import judge  # noqa: E402
import fixture  # noqa: E402


def nodes_of(tree):
    out = []
    for node in tree:
        out.append(node)
        out.extend(nodes_of(node["children"]))
    return out


def outline(tree, depth=0):
    lines = []
    for node in tree:
        lines.append("  " * depth + node["solution"])
        lines.extend(outline(node["children"], depth + 1))
    return lines


def dig(data, path):
    for part in path.split("."):
        try:
            data = data[int(part)] if isinstance(data, list) else data[part]
        except (KeyError, IndexError, ValueError, TypeError):
            return "<missing>"
    return data


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        records = fixture.TABLES if args["records"] == "tables" else None
        view = arm.view(fixture.EVENTS[args["events"]], records, args.get("expanded", ()))
        nodes = nodes_of(view["tree"])
        check = args["check"]
        if check == "outline":
            return {"outline": outline(view["tree"])}
        if check == "unplaced":
            return {"unplaced": [a["agent_id"] for a in view["unplaced"]]}
        if check == "agents_of":
            found = next((n for n in nodes if n["solution"] == args["solution"]), {"agents": []})
            return {"agents": [a["agent_id"] for a in found["agents"]], "nodes": [n["solution"] for n in nodes]}
        if check == "node":
            found = next((n for n in nodes if n["solution"] == args["solution"]), None)
            return {p: dig(found, p) if found is not None else "<no node>" for p in args["paths"]}
        if check == "collapsed":
            text = json.dumps(view)
            return {"nodes_with_detail": sum("detail" in n for n in nodes), "field_text_found": [t for t in fixture.FIELD_TEXTS if t in text]}
        if check == "expanded_ids":
            return {"expanded": view["expanded"], "nodes_with_detail": sum("detail" in n for n in nodes)}
        return {p: dig(view, p) for p in args["paths"]}

    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in sorted({r.get("kind") for r in rows})}
