"""Scores a cards-from-files arm with one number: the same cards, shown through a fixed selector, must serve three kinds of case.

The corpus is every ``.py`` file of Quest AI Runner and the hub package at the commits of ``datasets/qar_pin.json`` (``corpus.py``
reads them with ``git archive`` and checks the pinned digests). The case set mixes three kinds with the weights of ``mix.py``:

* ``file``: the 63 file-finding tasks of QAR's context-selection component at that commit, right when the needed file is among the first
  three files of the view. A card per file wins this kind by construction, so it is a floor for finding a file.
* ``topic``: commit subjects of QAR's git history that name no file or identifier (``topic_cases.py``), the files the commit changed
  being the needed set; right when half of them are inside the first three cards (``topic_kind.py``). This is what topic cards are for.
* ``orientation``: the file-finding tasks again, right when a file of the target's own folder is among the first three files
  (``orientation_kind.py``), a free proxy.

The builder is called once, on the first case, with the corpus root, the files in walk order and no existing cards; its cost and seconds
land on the first scored case, as one build serves every case of a run. The fixed selector (``selector.py``) is QAR's keyword IDF card
store, confidence gate off, ten cards in view; the view is the picked cards in rank order, each card's files in the builder's own order.

Store size is a term of the one number. A store that approaches one card per file, or the 1,000 cards the Quest store holds, gives up that
share of every case: ``store_penalty`` is the square of the cards per file (one when the cards exceed the store limit), and a case is
counted when it is right and its fixed place in [0, 1) (a hash of the case id) is at or above the penalty. A card per file therefore
scores nothing and a topic store of a tenth of the files loses about one case in a hundred. The balanced score then weighs that accuracy,
cost and time by ``[balance.cards_from_files]`` in ``esoi.toml``. The details give each kind's raw result, the store and the build.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import time

from cards_from_files import corpus as pinned
from cards_from_files import mix, orientation_kind, topic_cases, topic_kind
from cards_from_files.selector import Selector

TOP = 3
WIDE = 10


STORE_LIMIT = 1000   # the cards a Quest store holds
STORE_EXPONENT = 2   # the penalty grows as (cards per file) to this power


def load_cases():
    """The mixed case set: ``mix.counts`` of each kind, every case carrying its ``kind``."""
    files = [dict(c, kind="file") for c in pinned.load().cases]
    pools = dict(file=files, topic=[dict(c, kind="topic") for c in topic_cases.load()],
                 orientation=[dict(c, kind="orientation", id="ORI-" + c["id"]) for c in files])
    wanted = mix.counts({kind: len(cases) for kind, cases in pools.items()})
    return [case for kind in ("file", "orientation", "topic") for case in pools[kind][:wanted[kind]]]


def store_penalty(stored, files):
    """The share every case gives up for a store of ``stored`` cards over ``files`` files."""
    return 1.0 if stored > STORE_LIMIT else min(1.0, (stored / max(files, 1)) ** STORE_EXPONENT)


def place(case_id):
    """The fixed place of a case in [0, 1), the same every run."""
    return int(hashlib.sha256(str(case_id).encode()).hexdigest()[:8], 16) / 16 ** 8


def build_id(cards) -> str:
    """Eight hex characters naming a build: the same cards, in the same order, give the same id."""
    text = json.dumps([[c["id"], [f["path"] if isinstance(f, dict) else f for f in c.get("files", [])]] for c in cards])
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def distinct(view):
    """The files of a view in view order, each once (a file two cards both list counts at its first place)."""
    seen, out = set(), []
    for path in view:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


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


def view_function(builder, meter, replayed=None, saved=None):
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
            state["stored"] = len(cards)
            build = dict(cards=len(cards), id=build_id(cards), calls=after[0] - before[0], tokens=after[1] + after[2] - before[1] - before[2],
                         cost=round(after[3] - before[3], 4), seconds=round(seconds, 1))
            if replayed:
                build["replayed"] = dict(replayed)
            if saved:
                build["saved"] = dict(saved)
        picked = state["selector"].picked(args["task"])
        return dict(view=[path for card in picked for path in card], cards=picked, build=build, stored=state["stored"])
    return fn


def adapt(implementation, meter):
    """The harness hands a declared arm's class: a builder that needs a model is given the meter-wrapped provider the hub resolves
    for the ``call-a-model`` seat; one that needs nothing is simply built. An arm that returns a saved build of its own (``charged()``)
    is charged that build's model calls, tokens and cost on the meter, so the balanced score carries what the build cost."""
    instance = implementation(**needs(implementation, meter))
    replayed = instance.replayed() if hasattr(instance, "replayed") else None
    charge = instance.charged() if hasattr(instance, "charged") else None
    builder = instance.build
    if charge and meter is not None:
        def builder(root, files, existing, build=instance.build):
            cards = build(root, files, existing)
            meter.calls += charge["calls"]
            meter.tokens_in += charge["tokens_in"]
            meter.tokens_out += charge["tokens_out"]
            meter.cost_usd += charge["cost"]
            return cards
    return view_function(builder, meter, replayed, charge)


SAVED_BUILD_ENVIRONMENT = "CARDS_FROM_FILES_SAVED_BUILD"   # set to 1: score an arm's persisted build instead of building


def needs(implementation, meter):
    import inspect
    import os
    parameters = inspect.signature(implementation).parameters
    found = {}
    if "pin" in parameters:   # a replaying builder is told which corpus is in force and refuses another
        found["pin"] = pinned.read_pin()
    if "saved_build" in parameters and os.environ.get(SAVED_BUILD_ENVIRONMENT) == "1":
        found["saved_build"] = True
    if "provider" in parameters:
        from esoi import runtime
        from hubofhubs import seats  # noqa: F401  (declares the seats)
        provider_class = runtime.resolve("call-a-model", scope="hubofhubs")   # resolve returns the class: build the instance the meter wraps
        provider = provider_class(claude_path="claude", timeout_seconds=300, environment=dict(os.environ))
        found["provider"] = meter.wrap(provider, ("answer",))
    return found


def judge_file(got, case):
    view, target = got["view"], case["target"]
    rank = view.index(target) + 1 if target in view else None
    return dict(raw=bool(rank and rank <= TOP), top1=rank == 1, top10=bool(rank and rank <= WIDE), anywhere=rank is not None, rank=rank,
                got=f"rank {rank}" if rank else "not in view", note=f"{target} <- {view[0] if view else 'nothing'}")


JUDGES = {"file": judge_file, "topic": topic_kind.judge, "orientation": orientation_kind.judge}


def score_case(fn, case):
    kind = case.get("kind", "file")
    got = fn("view", {"task": case["task"]})
    row = JUDGES[kind](got, case)
    penalty = store_penalty(got["stored"], len(pinned.load().files)) if "stored" in got else 0.0
    row.update(kind=kind, penalty=round(penalty, 4), view=len(got["view"]), ok=bool(row["raw"] and place(case["id"]) >= penalty))
    if not row["ok"] and row["raw"]:
        row["got"] += f" (store penalty {penalty:.2f})"
    if got["build"]:
        row["build"] = got["build"]
        row["stored"] = got["stored"]
    return row


def aggregate(rows):
    """The details of a run: each kind's raw result and the number it counts, the store, the topic numbers and the build."""
    def of(kind):
        mine = [r for r in rows if r.get("kind", "file") == kind]
        return mine, f"{sum(bool(r['raw']) for r in mine)}/{len(mine)}", sum(bool(r['ok']) for r in mine)
    out = {}
    for kind in ("file", "topic", "orientation"):
        mine, raw, counted = of(kind)
        if mine:
            out[f"{kind}_raw"] = raw
            out[f"{kind}_counted"] = counted
    built = next((r for r in rows if r.get("build")), None)
    if built:
        out.update(store_penalty=rows[0]["penalty"], cards=built["build"]["cards"],
                   cards_per_file=round(built["stored"] / len(pinned.load().files), 3))
    out.update(topic_kind.summarize(rows))
    files = [r for r in rows if r.get("kind", "file") == "file" and "top1" in r]
    if files:
        out.update(file_top1=sum(bool(r["top1"]) for r in files), file_top10=sum(bool(r["top10"]) for r in files))
    out = dict(source=saved_note(rows), **out) if saved_note(rows) else out
    out.update(build_headline(rows))
    return out


def saved_note(rows):
    build = next((r["build"] for r in rows if r.get("build")), None)
    if build and build.get("saved"):
        return f"scored from the saved build {build['saved']['build']} (one stochastic build; replayed, no new model call)"
    return ""


def build_headline(rows):
    """The build facts every component of this family reports: cards built, the build's id, its calls, tokens, cost and seconds
    (charged to the first scored case) and, for a replay, the recorded build it came from."""
    build = next((r["build"] for r in rows if r.get("build")), None)
    out = {}
    if build:
        out.update(cards=build["cards"], build=build["id"], build_calls=build["calls"], build_tokens=build["tokens"],
                   build_cost=build["cost"], build_seconds=build["seconds"])
        if build.get("replayed"):
            was = build["replayed"]
            out["replayed"] = f"from build {was['build']} ({was['calls']} calls, ${was['cost']}, its cost and not this run's)"
    return out
