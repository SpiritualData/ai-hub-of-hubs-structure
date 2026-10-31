"""Scores a card-store arm: a fresh store, some cards added, one operation, the result compared with the written expectation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

from hubofhubs.card import Card  # noqa: E402


def run(build, args):
    store = build()
    for card_id, text, tags in args["cards"]:
        store.add(Card(card_id, text, tags=tuple(tags)))
    op = args["op"]
    if op == "search":
        return [c.id for c in store.search(args.get("query", ""), args.get("limit", 10), args.get("tag", ""))]
    if op == "get":
        card = store.get(args["id"])
        return None if card is None else [card.id, card.text, list(card.tags)]
    if op == "delete":
        return [store.delete(args["id"]), store.count(), store.get(args["id"]) is None]
    return store.count()


def adapt(implementation, meter):
    return lambda kind, args: run(implementation, args)


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
