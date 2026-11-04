"""Scores a retrieval arm with one number: the same corpus, the same budget, four kinds of request.

The corpus is every ``.py`` file of Quest AI Runner and the hub at the pinned commits of ``cards_from_files`` (the same pin, read with
``git archive``, so the corpus is the one the card builders are measured on). The case sources (``mix.py``):

* ``file``: the 63 file-finding tasks of QAR's context-selection component: the needed text is the target file.
* ``topic``: commit subjects that name no file or identifier, the files the commit changed being the needed set. The commits are all newer than
  the history an arm may learn from (``cochange_history.json``), so any learning is split in time.
* ``orientation``: the same file tasks asked for the target's neighbourhood: right when a file of the target's folder is among the first three.
* ``none``: requests that need nothing from the corpus (``datasets/no_context.json``); the right answer is to return nothing.

Labels are graded: a file is *needed* (the target, or a file the commit changed), *helpful* (a file that imports or is imported by a needed
file) or irrelevant. For each request an arm returns units (chunks or files) best first within ``BUDGET_TOKENS``; the case's utility is
``0.60 recall + 0.25 nDCG@10 + 0.15 quiet`` (``mix.UTILITY``): recall of the needed files among the units returned, graded nDCG@10 over the files
in rank order, and one minus the share of the tokens shown that belong to irrelevant files (the noise a reader has to read past). A request that
needs no context scores 1 for returning nothing and loses the share of the budget it filled. Store size is a term: an index larger than the
corpus gives up share of every case (``store_penalty``). The balanced score then weighs accuracy, cost and time by ``[balance.context_retrieval]``.
"""
from __future__ import annotations

import hashlib
import json
import math
import posixpath
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cards_from_files import corpus as pinned  # noqa: E402
from cards_from_files import topic_cases  # noqa: E402
from context_retrieval import mix  # noqa: E402

DATASETS = Path(__file__).resolve().parent / "datasets"
STATE: dict = {}


def world():
    """The pinned corpus (path to text), the history and the import links used for labels, read once."""
    if not STATE:
        from hubofhubs.retrieval.units import import_links
        pin = pinned.load()
        files = {f: (pin.root / f).read_text(encoding="utf-8", errors="replace") for f in pin.files}
        STATE.update(files=files, history=topic_cases.load_history(), links=import_links(files), pin=pin)
    return STATE


def load_cases():
    pin = pinned.load()
    files = [dict(c, kind="file") for c in pin.cases]
    pools = dict(file=files, topic=[dict(c, kind="topic") for c in topic_cases.load()],
                 orientation=[dict(c, kind="orientation", id="ORI-" + c["id"]) for c in files],
                 none=[dict(c, kind="none") for c in json.loads((DATASETS / "no_context.json").read_text())])
    wanted = mix.counts({kind: len(cases) for kind, cases in pools.items()})
    return [case for kind in ("file", "topic", "orientation", "none") for case in pools[kind][:wanted[kind]]]


def place(case_id):
    return int(hashlib.sha256(str(case_id).encode()).hexdigest()[:8], 16) / 16 ** 8


def store_penalty(index_bytes, corpus_bytes):
    return min(1.0, (index_bytes / max(corpus_bytes, 1) / mix.STORE_RATIO_LIMIT) ** mix.STORE_EXPONENT)


def labels(case, links):
    """``(needed, helpful)`` file sets of a case."""
    if case["kind"] == "topic":
        needed = set(case["needed"])
    elif case["kind"] == "file":
        needed = {case["target"]}
    elif case["kind"] == "orientation":
        folder = posixpath.dirname(case["target"])
        needed = {f for f in world()["files"] if posixpath.dirname(f) == folder}
    else:
        return set(), set()
    helpful = {n for f in needed for n in links.get(f, ())} - needed if case["kind"] != "orientation" else set()
    return needed, helpful


def ndcg(files, needed, helpful, k=10):
    gain = lambda f: mix.GAINS["needed"] if f in needed else mix.GAINS["helpful"] if f in helpful else 0.0
    dcg = sum(gain(f) / math.log2(i + 2) for i, f in enumerate(files[:k]))
    ideal = sorted([mix.GAINS["needed"]] * len(needed) + [mix.GAINS["helpful"]] * len(helpful), reverse=True)[:k]
    best = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / best if best else 0.0


def utility(case, hits, links):
    """The graded utility of the units returned for a case, in 0..1, and the numbers behind it."""
    shown = sum(h["tokens"] for h in hits)
    if case["kind"] == "none":
        return max(0.0, 1.0 - shown / mix.BUDGET_TOKENS), dict(recall=0.0, ndcg=0.0, noise=shown / mix.BUDGET_TOKENS)
    if not hits:
        return 0.0, dict(recall=0.0, ndcg=0.0, noise=0.0)
    needed, helpful = labels(case, links)
    files = list(dict.fromkeys(h["file"] for h in hits))
    recall = (1.0 if any(f in needed for f in files[:3]) else 0.0) if case["kind"] == "orientation" else len(needed & set(files)) / len(needed)
    noise_tokens = sum(h["tokens"] for h in hits if h["file"] not in needed and h["file"] not in helpful)
    noise = noise_tokens / shown if shown else 0.0
    u = mix.UTILITY["recall"] * recall + mix.UTILITY["ndcg"] * ndcg(files, needed, helpful) + mix.UTILITY["quiet"] * (1.0 - noise)
    return u, dict(recall=recall, ndcg=ndcg(files, needed, helpful), noise=noise)


def needs_of(implementation, meter):
    import inspect
    import os
    found = {}
    if "provider" in inspect.signature(implementation).parameters:
        from esoi import runtime
        from hubofhubs import seats  # noqa: F401
        provider = runtime.resolve("call-a-model", scope="hubofhubs")(claude_path="claude", timeout_seconds=300, environment=dict(os.environ))
        found["provider"] = meter.wrap(provider, ("answer",))
    return found


def adapt(implementation, meter, **settings):
    """``fn(case)`` over an arm built once: the corpus is prepared on the first case (its seconds land there, as one build serves every case)."""
    arm = implementation(**needs_of(implementation, meter), **settings)

    def fn(case):
        state = world()
        built = None
        if arm.corpus is None:
            started = time.time()
            arm.prepare(state["files"], state["history"])
            built = round(time.time() - started, 1)
        hits = arm.retrieve(case["task"], budget_tokens=mix.BUDGET_TOKENS)
        return dict(hits=[dict(file=h.file, tokens=h.tokens, id=h.id) for h in hits], index_bytes=arm.index_bytes(), build=built,
                    size=arm.corpus.size_bytes, units=len(arm.corpus.units), extra=getattr(arm, "trained_on", 0))
    return fn


def score_case(fn, case):
    got = fn(case)
    u, parts = utility(case, got["hits"], world()["links"])
    penalty = store_penalty(got["index_bytes"], got["size"])
    counted = u * (1.0 - penalty)
    shown = sum(h["tokens"] for h in got["hits"])
    row = dict(ok=bool(counted > place(case["id"])), kind=case["kind"], utility=round(u, 4), counted=round(counted, 4), penalty=round(penalty, 4),
               shown=shown, returned=len(got["hits"]), recall=round(parts["recall"], 4), ndcg=round(parts["ndcg"], 4), noise=round(parts["noise"], 4),
               got=f"{len(got['hits'])} units, {shown} tokens, utility {u:.2f}",
               note=(f"needs {len(labels(case, world()['links'])[0])} files" if case["kind"] != "none" else "needs no context"))
    if got["build"] is not None:
        row.update(build_seconds=got["build"], index_bytes=got["index_bytes"], units=got["units"])
    return row


def aggregate(rows):
    """The details of a run: each kind's mean utility and counted share, the means behind the utility and the store."""
    out = {}
    for kind in ("file", "topic", "orientation", "none"):
        mine = [r for r in rows if r.get("kind") == kind]
        if mine:
            out[f"{kind}_utility"] = round(statistics.mean(r["utility"] for r in mine), 4)
            out[f"{kind}_counted"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    real = [r for r in rows if r.get("kind") != "none"]
    if real:
        out.update(recall=round(statistics.mean(r["recall"] for r in real), 4), ndcg=round(statistics.mean(r["ndcg"] for r in real), 4),
                   noise=round(statistics.mean(r["noise"] for r in real), 4))
    out.update(mean_utility=round(statistics.mean(r["utility"] for r in rows), 4), mean_counted=round(statistics.mean(r["counted"] for r in rows), 4))
    built = next((r for r in rows if "build_seconds" in r), None)
    if built:
        out.update(store_penalty=built["penalty"], index_mb=round(built["index_bytes"] / 1e6, 1), units=built["units"], build_seconds=built["build_seconds"])
    return out
