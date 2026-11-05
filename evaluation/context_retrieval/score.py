"""Scores a retrieval arm with one number: the same budget, seven kinds of request over three kinds of world.

Worlds: the main corpus (every ``.py`` file of the pinned consumer runner and the hub at the pinned commits of ``cards_from_files``, read with ``git archive``);
three public Python repositories at pinned commits (``open_code.py``); and, per question, one user's timestamped chat history (``memory.py``, from
LongMemEval). The case sources (``mix.py``):

* ``file``: the 63 file-finding tasks of the main corpus's context-selection component: the needed text is the target file.
* ``topic``: commit subjects that name no file or identifier, the files the commit changed being the needed set, all newer than the history an arm
  may learn from (``cochange_history.json``).
* ``orientation``: the same file tasks asked for the target's neighbourhood: right when a file of the target's folder is among the first three.
* ``none``: requests that need nothing from the corpus (``datasets/no_context.json``); the right answer is to return nothing.
* ``topic_open``: the same kind of topic request over the public repositories, the focus being the repository the commit belongs to.
* ``grouping``: the same, made while working in a sibling repository: the needed files are at home elsewhere than the request's focus.
* ``memory``: a question about a user's chat history; evidence turns are needed, an outdated fact is irrelevant, an unanswered question needs nothing.

Labels are graded: *needed*, *helpful* (an import neighbour of a needed file, or the rest of a needed chat session) or irrelevant. For each request an
arm returns units best first within ``BUDGET_TOKENS``; the utility is ``0.60 recall + 0.25 nDCG@10 + 0.15 quiet`` (``mix.UTILITY``). A request that
needs no context scores 1 for returning nothing and loses the share of the budget it filled. Store size is a term (``store_penalty``), and so is what
an arm reads from the live sources while answering (``source_usd``, charged to the cost). The balanced score weighs accuracy, cost and time by
``[balance.context_retrieval]``.
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
from context_retrieval import memory, mix, open_code  # noqa: E402

DATASETS = Path(__file__).resolve().parent / "datasets"
STATE: dict = {}
KINDS = ("file", "topic", "orientation", "none", "topic_open", "grouping", "memory")   # the order cases run in: a corpus is prepared once per run of a world


def world():
    """The main corpus (path to text), the history and the import links used for labels, read once."""
    if "main" not in STATE:
        from hubofhubs.retrieval.units import import_links
        pin = pinned.load()
        files = {f: (pin.root / f).read_text(encoding="utf-8", errors="replace") for f in pin.files}
        history = topic_cases.load_history()
        STATE.update(main=dict(files=files, history=history, links=import_links(files), pin=pin, meta=main_meta(files, history), key="main"))
    return STATE["main"]


def main_meta(files, history):
    """Item metadata that is free for the main corpus: kind ``file``, a home (the hub package or the rest) and the date of the last commit of the
    history that changed the file (none for a file no commit of the history changed, so no date lies after the history)."""
    last = {}
    for commit in sorted(history, key=lambda c: str(c.get("date", ""))):
        for f in commit.get("files", []):
            last[f] = commit["date"]
    return {f: dict(kind="file", affinity_tags=["home:hub" if f.startswith(pinned.HUB_PACKAGE + "/") else "home:library"],
                    **({"timestamp": last[f]} if f in last else {})) for f in files}


def world_for(case):
    """The world a case is asked in: the main corpus, the public repositories (``topic_open``, ``grouping``) or one user's history (``memory``)."""
    from hubofhubs.retrieval.units import import_links
    if case["kind"] == "memory":
        if STATE.get("memory", {}).get("key") != case["id"]:
            files, meta = memory.world_of(case)
            STATE["memory"] = dict(files=files, history=[], links=import_links(files), meta=meta, key=case["id"])
        return STATE["memory"]
    if case["kind"] in ("topic_open", "grouping"):
        if "open" not in STATE:
            loaded = open_code.load()
            STATE["open"] = dict(files=loaded["files"], history=loaded["history"], links=import_links(loaded["files"]), meta=loaded["meta"], key="open")
        return STATE["open"]
    return world()


def load_cases():
    pin = pinned.load()
    files = [dict(c, kind="file") for c in pin.cases]
    opened = open_code.cases()
    pools = dict(file=files, topic=[dict(c, kind="topic") for c in topic_cases.load()],
                 orientation=[dict(c, kind="orientation", id="ORI-" + c["id"]) for c in files],
                 none=[dict(c, kind="none") for c in json.loads((DATASETS / "no_context.json").read_text())],
                 topic_open=opened["topic_open"], grouping=opened["grouping"], memory=memory.cases())
    wanted = mix.counts({kind: len(cases) for kind, cases in pools.items()})
    return [case for kind in KINDS for case in pools[kind][:wanted[kind]]]


def place(case_id):
    return int(hashlib.sha256(str(case_id).encode()).hexdigest()[:8], 16) / 16 ** 8


def store_penalty(index_bytes, corpus_bytes):
    return min(1.0, (index_bytes / max(corpus_bytes, 1) / mix.STORE_RATIO_LIMIT) ** mix.STORE_EXPONENT)


def labels(case, links):
    """``(needed, helpful)`` file sets of a case."""
    if case["kind"] == "memory":
        return set(case["needed"]), set(case["helpful"])
    if case["kind"] in ("topic", "topic_open", "grouping"):
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


def needs_nothing(case):
    """A request the corpus cannot answer: return nothing (a no-context request, or a question never answered in the history)."""
    return case["kind"] == "none" or (case["kind"] == "memory" and case["abstention"])


def ndcg(files, needed, helpful, k=10):
    gain = lambda f: mix.GAINS["needed"] if f in needed else mix.GAINS["helpful"] if f in helpful else 0.0
    dcg = sum(gain(f) / math.log2(i + 2) for i, f in enumerate(files[:k]))
    ideal = sorted([mix.GAINS["needed"]] * len(needed) + [mix.GAINS["helpful"]] * len(helpful), reverse=True)[:k]
    best = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / best if best else 0.0


def utility(case, hits, links):
    """The graded utility of the units returned for a case, in 0..1, and the numbers behind it."""
    shown = sum(h["tokens"] for h in hits)
    if needs_nothing(case):
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


def source_usd(counts):
    """The charge for what an arm read from the sources while answering one request (``mix.SOURCE_*``): 0 for an arm that reads only its index."""
    return mix.SOURCE_CALL_USD * counts["calls"] + mix.SOURCE_RECORD_USD * counts["records"] + mix.SOURCE_MB_USD * counts["bytes"] / 1e6


def request_of(case):
    """What the request itself carries (``units.ITEM_META``): when it is asked, its focus and the scope it may read. Arms that ignore it are unchanged."""
    request = {}
    when = case.get("timestamp") or case.get("date")
    if when:
        request["timestamp"] = when
    if case.get("focus"):
        request["affinity_tags"] = list(case["focus"])
    if case.get("scope_tags"):
        request["scope_tags"] = list(case["scope_tags"])
    return request


def adapt(implementation, meter, **settings):
    """``fn(case)`` over an arm built once: a world's corpus is prepared when the case's world is not the arm's current one (its seconds land on
    that case, as one build serves every case of the world). What the arm reads from the sources per request is charged to the meter's cost."""
    arm = implementation(**needs_of(implementation, meter), **settings)
    current = [None]

    def fn(case):
        state = world_for(case)
        built = None
        if current[0] != state["key"]:
            started = time.time()
            arm.prepare(state["files"], state["history"], state["meta"])
            built = round(time.time() - started, 1)
            current[0] = state["key"]
        hits = arm.retrieve(case["task"], budget_tokens=mix.BUDGET_TOKENS, request=request_of(case))
        counts = arm.source.snapshot()
        counts["out_of_scope"] += arm.source.outside(arm.corpus, list(dict.fromkeys(h.file for h in hits)))
        meter.cost_usd += source_usd(counts)
        return dict(hits=[dict(file=h.file, tokens=h.tokens, id=h.id) for h in hits], index_bytes=arm.index_bytes(), build=built,
                    size=arm.corpus.size_bytes, units=len(arm.corpus.units), extra=getattr(arm, "trained_on", 0), source=counts,
                    records=len(arm.corpus.files), world=state["key"])
    return fn


def score_case(fn, case):
    got = fn(case)
    u, parts = utility(case, got["hits"], world_for(case)["links"])
    penalty = store_penalty(got["index_bytes"], got["size"])
    counted = u * (1.0 - penalty)
    src = got["source"]
    risky = (src["calls"] > mix.MAX_SOURCE_CALLS or src["records"] / max(got["records"], 1) > mix.MAX_SCAN_SHARE
             or src["out_of_scope"] > mix.MAX_OUT_OF_SCOPE)
    if risky:     # too many source calls, a full scan or a read outside the request's scope gives up the case
        counted = 0.0
    shown = sum(h["tokens"] for h in got["hits"])
    row = dict(ok=bool(counted > place(case["id"])), kind=case["kind"], utility=round(u, 4), counted=round(counted, 4), penalty=round(penalty, 4),
               shown=shown, returned=len(got["hits"]), recall=round(parts["recall"], 4), ndcg=round(parts["ndcg"], 4), noise=round(parts["noise"], 4),
               needs=not needs_nothing(case), source_calls=src["calls"], source_records=src["records"], source_mb=round(src["bytes"] / 1e6, 4),
               source_usd=round(source_usd(src), 6), risky=risky, scan_share=round(src["records"] / max(got["records"], 1), 4), out_of_scope=src["out_of_scope"],
               got=f"{len(got['hits'])} units, {shown} tokens, utility {u:.2f}",
               note=(f"needs {len(labels(case, world_for(case)['links'])[0])} files" if not needs_nothing(case) else "needs no context"))
    if case["kind"] == "memory":
        row["sub"] = "abstention" if case["abstention"] else case["question_type"]
    if got["build"] is not None:
        row.update(build_seconds=got["build"], index_bytes=got["index_bytes"], units=got["units"], world=got["world"])
    return row


def aggregate(rows):
    """The details of a run: each kind's mean utility and counted share, the means behind the utility, the store and the source access."""
    out = {}
    for kind in KINDS:
        mine = [r for r in rows if r.get("kind") == kind]
        if mine:
            out[f"{kind}_utility"] = round(statistics.mean(r["utility"] for r in mine), 4)
            out[f"{kind}_counted"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    for sub in sorted({r["sub"] for r in rows if r.get("sub")}):
        mine = [r for r in rows if r.get("sub") == sub]
        out[f"memory_{sub.replace('-', '_')}_utility"] = round(statistics.mean(r["utility"] for r in mine), 4)
    real = [r for r in rows if r.get("needs", r.get("kind") != "none")]
    if real:
        out.update(recall=round(statistics.mean(r["recall"] for r in real), 4), ndcg=round(statistics.mean(r["ndcg"] for r in real), 4),
                   noise=round(statistics.mean(r["noise"] for r in real), 4))
    out.update(mean_utility=round(statistics.mean(r["utility"] for r in rows), 4), mean_counted=round(statistics.mean(r["counted"] for r in rows), 4))
    built = next((r for r in rows if "build_seconds" in r), None)
    if built:
        out.update(store_penalty=built["penalty"], index_mb=round(built["index_bytes"] / 1e6, 1), units=built["units"],
                   build_seconds=round(sum(r.get("build_seconds", 0) for r in rows), 1))
    out.update(source_calls_max=max((r.get("source_calls", 0) for r in rows), default=0), source_calls_mean=round(statistics.mean(r.get("source_calls", 0) for r in rows), 2),
               source_usd_mean=round(statistics.mean(r.get("source_usd", 0.0) for r in rows), 6),
               scan_share_max=max((r.get("scan_share", 0.0) for r in rows), default=0.0), out_of_scope=sum(r.get("out_of_scope", 0) for r in rows),
               cases_by_kind="/".join(f"{k}:{sum(r.get('kind') == k for r in rows)}" for k in KINDS if any(r.get("kind") == k for r in rows)))
    return out
