"""The topic kind of case: do the top cards bundle the files a piece of work needed?

The cases (``topic_cases``) are commits of Quest AI Runner whose subject reads as a topic and names no file or identifier: the subject
is the task and the files the commit changed, as far as they are in the pinned corpus, are the needed set (two to eight files). A card is
the unit of retrieval: the fixed selector ranks the cards and the case reads the first three.

``judge`` records ``cov1`` and ``cov3`` (the share of the needed files inside the first card and inside the first three), ``noise3`` (the
share of the files of those three cards that are not needed) and, for a task whose needed files lie in more than one folder, ``bundled``
(one of the three cards holds needed files from two or more folders). The case is right (``raw``) when ``cov3`` is at least ``PASS_SHARE``
and the three cards hold at most ``MAX_VIEW_FILES`` distinct files, so one giant card cannot be right.
"""
from __future__ import annotations

import posixpath


TOP_ONE, TOP_THREE = 1, 3
PASS_SHARE = 0.5
MAX_VIEW_FILES = 30


def inside(needed, cards):
    held = set(path for card in cards for path in card)
    return len(set(needed) & held) / len(needed), held


def bundled(needed, cards):
    wanted = set(needed)
    return any(len({posixpath.dirname(p) for p in card if p in wanted}) >= 2 for card in cards)


def judge(got, case):
    cards, needed = got["cards"], case["needed"]
    cov1, _ = inside(needed, cards[:TOP_ONE])
    cov3, held = inside(needed, cards[:TOP_THREE])
    spans = len({posixpath.dirname(p) for p in needed}) >= 2
    return dict(raw=cov3 >= PASS_SHARE and len(held) <= MAX_VIEW_FILES, cov1=cov1, cov3=cov3,
                noise3=1 - len(held & set(needed)) / len(held) if held else 1.0, spans=spans,
                bundled=spans and bundled(needed, cards[:TOP_THREE]), view=len(held),
                got=f"{round(cov3 * len(needed))}/{len(needed)} needed files in the first three cards ({len(held)} files)",
                note=f"{len(needed)} needed, first card {len(cards[0]) if cards else 0} files")


def summarize(rows):
    """Headline numbers of the topic cases among ``rows`` (empty when there are none)."""
    mine = [r for r in rows if r.get("kind") == "topic"]
    if not mine:
        return {}
    mean = lambda key: round(sum(r[key] for r in mine) / len(mine), 4)
    spanning = [r for r in mine if r["spans"]]
    return dict(cov1=mean("cov1"), cov3=mean("cov3"), noise3=mean("noise3"), bundled=f"{sum(bool(r['bundled']) for r in spanning)}/{len(spanning)}")
