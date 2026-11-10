"""Scores a Frontend Interface arm: does each event and control of a session reach a frontend as plain data, with the run facts, and nothing of a terminal?

Each case (``build_cases.py``) names a check: ``event`` and ``control`` send one dict through JSON and back (the arm encodes it, ``json`` carries it, the arm
decodes it, the dict of the result must equal the original); ``facts`` reads paths (``cost.usd``, ``helpers.0.state``) out of the picture of the events and controls;
``leak`` looks for terminal markers (an escape code, a key hint, the name of the terminal screen) and checks that the picture is plain JSON. A case passes when the
result equals the expected values written by hand. One number: the share of cases right, balanced with cost and time by ``[balance.frontend_interface]``. No model
call, no network. What it cannot see: whether a real frontend draws the data well; the list of terminal markers is fixed."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

MARKERS = ("\x1b", "Esc stop", "type + Enter", "ahohs", "[y] approve", "taken up yet", "●")


def plain_json(value):
    try:
        return json.loads(json.dumps(value)) == value
    except (TypeError, ValueError):
        return False


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
        check = args["check"]
        if check in ("event", "control"):
            encode, decode = (arm.encode_event, arm.decode_event) if check == "event" else (arm.encode_control, arm.decode_control)
            wire = encode(decode(args["data"]))
            carried = json.loads(json.dumps(wire))
            return {"round_trip": carried == args["data"] and decode(carried).to_dict() == args["data"], "plain": plain_json(wire)}
        picture = arm.snapshot(args["events"], args["controls"])
        if check == "leak":
            text = json.dumps(picture)
            return {"leaks": [m for m in MARKERS if m in text], "plain": plain_json(picture)}
        return {path: dig(picture, path) for path in args["paths"]}

    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in sorted({r.get("kind") for r in rows})}
