"""Scores an Objectives arm: given the person's recorded objectives, does it return the hierarchy rolled up as the stated rule gives it, and put a request under the
objective it serves?

The cases are rules written with invented neutral objectives (``build_cases.py`` says which rule each exercises). One number: the share of cases whose whole answer
equals the reviewed one, balanced with cost and time by ``[balance.live_objectives]`` (accuracy 70%, cost 15%, time 15%, fixed before any arm was scored). No model
call, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        if kind == "rollup":
            return [[r["id"], r["depth"], r["state"], r["progress"]] for r in arm.current(objectives=args["objectives"])]
        found = arm.place(args["request"], objectives=args["objectives"])
        return [found["objective"], found["path"]]
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in sorted({r.get("kind") for r in rows})}
