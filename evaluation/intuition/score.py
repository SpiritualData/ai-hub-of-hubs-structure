"""Scores an Intuition arm: does what it offers unasked contain the useful items and little else?

Cases are invented and neutral (``build_cases.py``, source tag ``invented-neutral``): a store of cards, a log of what was taken for earlier requests, a request and a limit.
Per case the score is the F1 of the offered ids against the useful ids (precision and recall weighted equally, fixed before any arm was scored); a case that needs nothing
scores 1 for offering nothing and 0 otherwise. A case passes at F1 0.5 or more. The one number is the share of cases passed; ``details`` carries the mean F1 and the
share passed per kind. No model call, no network."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS_AT = 0.5


class Context:
    """The smallest Internal Context an arm can be handed in a case: the cards as one corpus."""

    def __init__(self, cards):
        self.texts = {card["id"]: card["text"] for card in cards}

    def corpus(self):
        return dict(self.texts)


def adapt(implementation, meter):
    def run(kind, args):
        context = Context(args["cards"])
        takes = {"history": args["history"]} if "history" in inspect.signature(implementation).parameters else {}
        return [item["id"] for item in implementation(context, **takes).offer(args["request"], limit=args["limit"])]
    return run


def f1(got, want):
    if not want:
        return 1.0 if not got else 0.0
    hit = len(set(got) & set(want))
    if not hit:
        return 0.0
    precision, recall = hit / len(got), hit / len(want)
    return 2 * precision * recall / (precision + recall)


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    value = f1(got, case["expect"])
    return dict(ok=value >= PASS_AT, f1=round(value, 4), kind=case["kind"], got=",".join(got)[:60], note="" if value >= PASS_AT else f"expected {','.join(case['expect'])}")


def aggregate(rows):
    out = {"mean_f1": round(sum(r["f1"] for r in rows) / max(len(rows), 1), 4)}
    for kind in sorted({r["kind"] for r in rows}):
        out[f"{kind}_passed"] = f"{sum(bool(r['ok']) for r in rows if r['kind'] == kind)}/{sum(r['kind'] == kind for r in rows)}"
    return out
