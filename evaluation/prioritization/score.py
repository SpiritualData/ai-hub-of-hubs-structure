"""Scores a Prioritization arm: do the candidates come back in the order the rule of the case gives them?

The cases are invented, neutral cases that each exercise one generic rule (``build_cases.py`` names the rule of each); a consumer's own rules are scored by its
own arm and cases built on this metric. One number: the share of cases whose whole order equals the reviewed order, balanced with cost and time by ``[balance.prioritization]``
(accuracy 70%, cost 15%, time 15%, fixed before any arm was scored). ``details`` also reports the mean pairwise agreement (the share of item pairs placed in the
reviewed order), so a near miss shows. No model call, no network."""
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    arm = implementation()
    return lambda kind, args: [item["id"] for item in arm.prioritize(person=args["person"], candidates=args["candidates"], stated=args.get("stated"), now=args["now"])["ordered"]]


def agreement(got, want):
    """The share of pairs of wanted items that ``got`` places in the wanted order (a missing item counts as out of order)."""
    pairs = list(combinations(want, 2))
    if not pairs:
        return 1.0
    place = {ident: n for n, ident in enumerate(got)}
    return sum(a in place and b in place and place[a] < place[b] for a, b in pairs) / len(pairs)


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    return dict(judge(got, case), kind=case["kind"], agreement=round(agreement(got, case["expect"]), 4))


def aggregate(rows):
    out = {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in sorted({r.get("kind") for r in rows})}
    out["mean_pairwise_agreement"] = round(sum(r.get("agreement", 0.0) for r in rows) / max(len(rows), 1), 4)
    return out
