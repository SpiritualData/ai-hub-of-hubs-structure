"""Scores a Terminal Session arm: does a scripted-stdin session come out right?

Each case feeds lines through the arm with a stub front door that answers from the case. A session is right when every typed line that is not a command reaches the
front door in order and only those, every text the person should see is shown, the exit code is 0 and the session ended with its closing line. One number: the share of
sessions that are right, balanced with time by ``[balance.terminal_session]`` (accuracy 70%, cost 15%, time 15%, fixed before any arm was scored). No model call, no network."""
import io
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from offline import judge  # noqa: E402

from esoi import Pending  # noqa: E402
from hubofhubs.the_world.tools.deep import ProgressEvent  # noqa: E402


@dataclass
class Reply:
    answer: str = ""
    events: tuple = ()
    note: str = ""


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        if kind == "pty":       # the real entry: ahohs work on a pseudo-terminal, a real fast-tier session
            from pty_stage import run_pty_case
            return {"failed": run_pty_case(implementation, args["scenario"], meter)}
        if kind == "attend":
            from sessions import run_scenario
            return {"failed": run_scenario(arm, args["scenario"], args["kit"])}
        calls = []

        def door(text):
            calls.append(text)
            if args.get("setup_error"):
                raise Pending("hub-of-hubs", ["set SOME_KEY"])
            spec = args["replies"].get(text, {})
            return Reply(spec.get("answer", ""), tuple(ProgressEvent(type=e["type"], text=e["text"], data=e["data"]) for e in spec.get("events", [])))

        out = io.StringIO()
        code = arm.converse(door, io.StringIO("".join(args["lines"])), out)
        shown = out.getvalue()
        return {"door_calls": calls, "missing": [t for t in args["must_show"] if t not in shown], "exit_code": code,
                "ended": shown.rstrip().endswith("Goodbye.")}

    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"], requirements=case.get("requirements", []))


def aggregate(rows):
    wanted = sorted({x for r in rows for x in r.get("requirements", [])}, key=lambda x: int(x[1:]))
    by_req = {x: f"{sum(bool(r['ok']) for r in rows if x in r.get('requirements', []))}/{sum(x in r.get('requirements', []) for r in rows)}" for x in wanted}
    return {**by_req, **{f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in sorted({r.get("kind") for r in rows})}}

