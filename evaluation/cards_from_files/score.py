"""Scores a cards-from-files arm: a builder's cards, shown through a fixed selector, must lead to the file a task needs.

The corpus is every ``.py`` file of Quest AI Runner and the hub package at the commits of ``datasets/qar_pin.json`` (``corpus.py``
reads them with ``git archive`` and checks the pinned digests). The cases are the 63 file-finding tasks of QAR's context-selection
component at that commit. The builder is called once, on the first case, with the corpus root, the files in walk order and no
existing cards; its cost and seconds therefore land on the first scored case, as one build serves every case of a run.

The fixed selector (``selector.py``) is QAR's keyword IDF card store, confidence gate off, ten cards in view. The view of a task is
the picked cards in rank order, each card's files in the builder's own order. A case passes when the needed file is among the
first three files of that view; the details also give the first ten files, the file anywhere in the view, the median and largest
view, and the build (cards, its id, model calls, tokens, cost, seconds). A builder that puts many files in one card pushes the
needed file out of the first three, so a degenerate grouping passes nothing.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import time

from cards_from_files import corpus as pinned
from cards_from_files.selector import Selector

TOP = 3
WIDE = 10


def load_cases():
    return pinned.load().cases


def build_id(cards) -> str:
    """Eight hex characters naming a build: the same cards, in the same order, give the same id."""
    text = json.dumps([[c["id"], [f["path"] if isinstance(f, dict) else f for f in c.get("files", [])]] for c in cards])
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def check_cards(cards, files) -> None:
    """A builder must return cards with unique ids that name only files of the corpus; anything else is the builder's defect."""
    known = set(files)
    if not isinstance(cards, list) or not all(isinstance(c, dict) for c in cards):
        raise ValueError("a builder returns a list of card records")
    ids = [c.get("id") for c in cards]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("every card needs its own id")
    for card in cards:
        for entry in card.get("files", []):
            path = entry["path"] if isinstance(entry, dict) else entry
            if path not in known:
                raise ValueError(f"card {card['id']!r} names {path!r}, which is not a file of the corpus")


def view_function(builder, meter, replayed=None):
    """``fn(kind, args)`` for a ``builder(root, files, existing) -> cards``: it builds on its first call, then answers each task's view.
    ``meter`` (None allowed) is read for the build's model calls, tokens and cost. ``replayed`` (None for a real build) names the
    recorded build a replaying builder returns (``build``, ``calls``, ``cost``); it is reported beside the build, never as this run's cost."""
    state = {}

    def fn(kind, args):
        corpus = pinned.load()
        build = None
        if not state:
            before = (meter.calls, meter.tokens_in, meter.tokens_out, meter.cost_usd) if meter else (0, 0, 0, 0.0)
            started = time.time()
            cards = builder(str(corpus.root), list(corpus.files), {})
            seconds = time.time() - started
            check_cards(cards, corpus.files)
            after = (meter.calls, meter.tokens_in, meter.tokens_out, meter.cost_usd) if meter else (0, 0, 0, 0.0)
            state["selector"] = Selector(cards, corpus)
            build = dict(cards=len(cards), id=build_id(cards), calls=after[0] - before[0], tokens=after[1] + after[2] - before[1] - before[2],
                         cost=round(after[3] - before[3], 4), seconds=round(seconds, 1))
            if replayed:
                build["replayed"] = dict(replayed)
        return dict(view=state["selector"].view(args["task"]), build=build)
    return fn


def adapt(implementation, meter):
    """The harness hands a declared arm's class: a builder that needs a model is given the meter-wrapped provider the hub resolves
    for the ``call-a-model`` seat; one that needs nothing is simply built."""
    instance = implementation(**needs(implementation, meter))
    replayed = instance.replayed() if hasattr(instance, "replayed") else None
    return view_function(instance.build, meter, replayed)


def needs(implementation, meter):
    import inspect
    parameters = inspect.signature(implementation).parameters
    if "pin" in parameters:   # a replaying builder is told which corpus is in force and refuses another
        return dict(pin=pinned.read_pin())
    if "provider" not in parameters:
        return {}
    from esoi import runtime
    from hubofhubs import seats  # noqa: F401  (declares the seats)
    import os
    provider_class = runtime.resolve("call-a-model", scope="hubofhubs")   # resolve returns the class: build the instance the meter wraps
    provider = provider_class(claude_path="claude", timeout_seconds=300, environment=dict(os.environ))
    return dict(provider=meter.wrap(provider, ("answer",)))


def score_case(fn, case):
    got = fn("view", {"task": case["task"]})
    view, target = got["view"], case["target"]
    rank = view.index(target) + 1 if target in view else None
    row = dict(ok=bool(rank and rank <= TOP), top1=rank == 1, top10=bool(rank and rank <= WIDE), anywhere=rank is not None, rank=rank,
               view=len(view), got=f"rank {rank}" if rank else "not in view", note=f"{target} <- {view[0] if view else 'nothing'}")
    if got["build"]:
        row["build"] = got["build"]
    return row


def aggregate(rows):
    n = len(rows)
    count = lambda key: sum(bool(r.get(key)) for r in rows)
    sizes = sorted(r["view"] for r in rows)
    build = next((r["build"] for r in rows if r.get("build")), None)
    out = dict(top1=f"{count('top1')}/{n}", top10=f"{count('top10')}/{n}", anywhere=f"{count('anywhere')}/{n}",
               view_median=int(statistics.median(sizes)) if sizes else 0, view_max=sizes[-1] if sizes else 0)
    if build:
        out.update(cards=build["cards"], build=build["id"], build_calls=build["calls"], build_tokens=build["tokens"],
                   build_cost=build["cost"], build_seconds=build["seconds"])
        if build.get("replayed"):
            was = build["replayed"]
            out["replayed"] = f"from build {was['build']} ({was['calls']} calls, ${was['cost']}, its cost and not this run's)"
    return out
