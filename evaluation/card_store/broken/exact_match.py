"""BASELINE: the naive store. Search is one exact, case-sensitive substring of the whole query, tags are ignored, and the limit is
applied before the filter. Zero model calls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def build(meter):
    def run(kind, args):
        cards = {cid: (text, tags) for cid, text, tags in args["cards"]}
        op = args["op"]
        if op == "search":
            first = list(cards)[: args.get("limit", 10)]
            return [cid for cid in first if args.get("query", "") in cards[cid][0]]
        if op == "get":
            return [args["id"], cards[args["id"]][0], cards[args["id"]][1]] if args["id"] in cards else None
        if op == "delete":
            return [args["id"] in cards, len(cards), True]
        return len(args["cards"])
    return run
