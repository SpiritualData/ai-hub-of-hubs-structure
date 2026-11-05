"""Scores a Planner arm: for a request taken from another seat's own case set, does the first piece name the worker that seat uses (or none)?

One component, one number: the share of requests routed to the right worker. The kinds are web-search questions, literature questions, coding goals, requests that
need no context and one two-step request whose pieces must each get the right worker. No model call, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        pieces = arm.plan(args["request"])
        tools = [str(p.get("tool", "")) for p in pieces]
        return tools if kind == "steps" else (tools[0] if tools else None)
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    out = {}
    for kind in sorted({r.get("kind") for r in rows} - {None}):
        mine = [r for r in rows if r.get("kind") == kind]
        out[f"{kind}_passed"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    return out
