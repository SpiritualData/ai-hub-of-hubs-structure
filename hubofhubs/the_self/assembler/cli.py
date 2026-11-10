"""``ahohs``: the hub's command line. ``ahohs chat`` is the line REPL of ``the_consciousness/ai_session_experience/terminal_experience/repl.py`` over the same call. ``ahohs run "<input>"`` is a thin wrapper over ``hubofhubs.run``: it runs the whole hub on the
input, or the solution named with ``--id``, and prints the answer with its sources (``--json`` prints one JSON object). Exit code 0
ran, 2 needs setup (the lines say what to set), 1 the run failed. Standard library only."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from esoi import EntryError, Pending

from hubofhubs.the_self.assembler.oneline import Result


def main(argv: Optional[List[str]] = None) -> int:
    import hubofhubs
    parser = argparse.ArgumentParser(prog="ahohs", description="Run the hub from one line.")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run", help="answer one input with the best-measured arm of the whole hub, or of one id")
    one.add_argument("input")
    one.add_argument("--id", default="hub-of-hubs", help="the solution or intent to run (default: the whole hub)")
    one.add_argument("--arm", action="append", default=[], metavar="ID=ARM", help="override one solution's arm")
    one.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    one.add_argument("--json", action="store_true", help="print the result as one JSON object")
    talk = sub.add_parser("chat", help="talk to the whole hub line by line (/help inside lists the commands)")
    talk.add_argument("--arm", action="append", default=[], metavar="ID=ARM", help="override one solution's arm")
    talk.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    args = parser.parse_args(argv)
    if args.command == "chat":
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.repl import LineRepl
        chosen = dict(item.split("=", 1) for item in args.arm)
        return LineRepl().converse(lambda text: hubofhubs.run("hub-of-hubs", text, arms=chosen or None, lock=args.lock), sys.stdin, sys.stdout)
    arms = dict(item.split("=", 1) for item in args.arm)
    try:
        result = hubofhubs.run(args.id, args.input, arms=arms or None, lock=args.lock)
    except Pending as error:
        print(error, file=sys.stderr)
        return 2
    except EntryError as error:
        print(f"failed: {error}", file=sys.stderr)
        return 1
    if isinstance(result, Result):
        if args.json:
            print(json.dumps({"type": "run", **result.to_dict()}))
            return 0
        print(result.answer)
        if result.note:
            print(f"({result.note})", file=sys.stderr)
        for item in result.items:
            print(f"- {item.get('title') or item.get('id', '')} {item.get('url') or item.get('doi') or ''}".rstrip())
        print("[" + ", ".join(f"{s}={a}" for s, a in result.arms.items()) + "]", file=sys.stderr)
    else:
        print(json.dumps(result, default=repr) if args.json else repr(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
