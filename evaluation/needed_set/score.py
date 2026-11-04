"""Scores a cards-from-files arm on topics: do the top cards bundle the files a piece of work needed, without a card per file?

The cases are 150 commits of Quest AI Runner (``cases.py``) whose subject reads as a topic and names no file or identifier: the
subject is the task and the files the commit changed, as far as they are in the pinned corpus, are the needed set (two to eight
files). A card is the unit of retrieval: the fixed selector of ``cards_from_files`` (shared through its ``score`` module; no arm or
plumbing is copied) ranks the cards and the case reads the first three.

Per case: ``cov1`` and ``cov3``, the share of the needed files inside the first card and inside the first three cards; ``noise3``, the
share of the files of those three cards that are not needed; ``bundled`` (only for a task whose needed files lie in more than one
folder), whether one of the three cards holds needed files from two or more folders. A case passes when ``cov3`` is at least
``PASS_SHARE`` and the three cards hold at most ``MAX_VIEW_FILES`` distinct files (a reader can take them in; one giant card fails
here). The details also give the store: ``cards`` and ``cards_per_file``. A builder whose store holds more than ``MAX_CARDS_PER_FILE``
cards per file is disqualified (``disqualify``: the run records a balanced score of zero): the Quest store caps at 1,000 cards and a
card per file is an index of files, not a topic.
"""
from __future__ import annotations

import posixpath
import statistics

from cards_from_files import corpus as pinned
from cards_from_files import score as family
from needed_set import cases as pinned_cases

TOP_ONE, TOP_THREE = 1, 3
PASS_SHARE = 0.5
MAX_VIEW_FILES = 30
MAX_CARDS_PER_FILE = 0.25

check_cards, build_id, adapt, view_function, distinct = family.check_cards, family.build_id, family.adapt, family.view_function, family.distinct


def load_cases():
    return pinned_cases.load()


def inside(needed, cards):
    held = set(path for card in cards for path in card)
    return len(set(needed) & held) / len(needed), held


def bundled(needed, cards):
    wanted = set(needed)
    return any(len({posixpath.dirname(p) for p in card if p in wanted}) >= 2 for card in cards)


def score_case(fn, case):
    got = fn("view", {"task": case["task"]})
    cards, needed = got["cards"], case["needed"]
    cov1, _ = inside(needed, cards[:TOP_ONE])
    cov3, held = inside(needed, cards[:TOP_THREE])
    noise = 1 - len(held & set(needed)) / len(held) if held else 1.0
    spans = len({posixpath.dirname(p) for p in needed}) >= 2
    row = dict(ok=cov3 >= PASS_SHARE and len(held) <= MAX_VIEW_FILES, cov1=cov1, cov3=cov3, noise3=noise, spans=spans,
               bundled=spans and bundled(needed, cards[:TOP_THREE]), view=len(held),
               got=f"{round(cov3 * len(needed))}/{len(needed)} needed files in the first three cards ({len(held)} files)",
               note=f"{len(needed)} needed, first card {len(cards[0]) if cards else 0} files")
    if got["build"]:
        row["build"] = got["build"]
    return row


def cards_per_file(rows):
    build = next((r["build"] for r in rows if r.get("build")), None)
    return build["cards"] / len(pinned.load().files) if build else None


def disqualify(rows):
    ratio = cards_per_file(rows)
    if ratio is not None and ratio > MAX_CARDS_PER_FILE:
        return f"{ratio:.2f} cards per file is above the cap of {MAX_CARDS_PER_FILE}: a store of one card per file is an index of files, not topic cards"
    return ""


def aggregate(rows):
    n = len(rows)
    mean = lambda key: round(sum(r[key] for r in rows) / n, 4)
    spanning = [r for r in rows if r["spans"]]
    sizes = sorted(r["view"] for r in rows)
    out = dict(cov1=mean("cov1"), cov3=mean("cov3"), noise3=mean("noise3"),
               bundled=f"{sum(bool(r['bundled']) for r in spanning)}/{len(spanning)}", view_median=int(statistics.median(sizes)) if sizes else 0)
    out.update(family.build_headline(rows))
    ratio = cards_per_file(rows)
    if ratio is not None:
        out["cards_per_file"] = round(ratio, 3)
    return out
