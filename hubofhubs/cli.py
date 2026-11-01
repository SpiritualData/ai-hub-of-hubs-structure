"""``ahohs``: the hub's command line. ``ahohs run "<input>"`` is a thin wrapper over ``hubofhubs.run``: events print as they happen
(plain lines) or, with ``--json``, as one JSON object per line ending with the result. Exit code 0 ran, 2 needs setup (the lines say
what to set), 1 the seat failed. Standard library only."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .oneline import Needs, RunFailed, run, seat_of
from .ports.events import EVENT_DECISION, EVENT_RESULT, EVENT_STATUS


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ahohs", description="Run the hub from one line.")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run", help="answer one input with the best-measured arm of a seat")
    one.add_argument("input")
    one.add_argument("--seat", default=None, help="ask (default, web-grounded), model, papers or recall")
    one.add_argument("--arm", action="append", default=[], metavar="SEAT=ARM", help="override one seat's arm")
    one.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    one.add_argument("--model", default=None)
    one.add_argument("--json", action="store_true", help="one JSON object per line: each event, then the result")
    args = parser.parse_args(argv)
    arms = dict(item.split("=", 1) for item in args.arm)

    def show(e) -> None:
        if args.json:
            print(json.dumps(e.to_dict()))
        elif e.type == EVENT_STATUS:
            print(f"... {e.text}", file=sys.stderr)
        elif e.type == EVENT_DECISION:
            print(f"needs setup: {e.text}", file=sys.stderr)

    try:
        result = run(args.input, args.seat, on_event=show, arms=arms or None, lock=args.lock, model=args.model)
    except Needs as error:
        if not args.json:
            print(error, file=sys.stderr)
        return 2
    except RunFailed as error:
        print(f"failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"type": "run", **result.to_dict()}))
    else:
        print(result.answer)
        if result.note:
            print(f"({result.note})", file=sys.stderr)
        for item in result.items:
            print(f"- {item.get('title') or item.get('id', '')} {item.get('url') or item.get('doi') or ''}".rstrip())
        print(f"[{result.seat}: " + ", ".join(f"{s}={a}" for s, a in result.arms.items()) + "]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
