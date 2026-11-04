"""Scores a cards-from-files arm on orientation: does the view put a reader in the part of the code the task is about?

A proxy, free and with no model: the cases are the 63 file-finding tasks of ``cards_from_files`` (one needed file each), and a case
asks for the neighbourhood of that file instead of the file. It passes when one of the first three files of the view is in the
target's own folder (``folder_hit``). The details also count ``area_hit``: the first card shown has files whose common folder is
the target's folder or its parent (never the root, which every card of spread files would reach). A one-file card is its own
folder, so it is an area hit when that file's folder is the target's folder or the target folder's parent.

The corpus, the builder's single build and the fixed selector (ten cards) are those of ``cards_from_files``; nothing is copied.
This measures nearness, not that a reader found the file, so it does not replace the file-finding metric; it is the part of what topic
cards are for that a single-file target cannot show.
"""
from __future__ import annotations

import posixpath
import statistics

from cards_from_files import score as family

FIRST = 3

load_cases, adapt, view_function, check_cards, build_id, distinct = (family.load_cases, family.adapt, family.view_function,
                                                                     family.check_cards, family.build_id, family.distinct)


def common_folder(paths):
    folders = [posixpath.dirname(p) for p in paths]
    return posixpath.commonpath(folders) if folders and all(folders) else ""


def area_hit(card, folder):
    here = common_folder(card)
    return bool(here) and (here == folder or here == posixpath.dirname(folder))


def score_case(fn, case):
    got = fn("view", {"task": case["task"]})
    view, folder = distinct(got["view"]), posixpath.dirname(case["target"])
    folder_hit = any(posixpath.dirname(path) == folder for path in view[:FIRST])
    first_card = got["cards"][0] if got.get("cards") else []
    row = dict(ok=folder_hit, folder_hit=folder_hit, area_hit=area_hit(first_card, folder), view=len(view),
               got="folder hit" if folder_hit else "no file of the folder in the first three",
               note=f"{folder or 'root'} <- {view[0] if view else 'nothing'}")
    if got["build"]:
        row["build"] = got["build"]
    return row


def aggregate(rows):
    n = len(rows)
    sizes = sorted(r["view"] for r in rows)
    out = dict(folder_hit=f"{sum(bool(r['folder_hit']) for r in rows)}/{n}", area_hit=f"{sum(bool(r['area_hit']) for r in rows)}/{n}",
               view_median=int(statistics.median(sizes)) if sizes else 0, view_max=sizes[-1] if sizes else 0)
    out.update(family.build_headline(rows))
    return out
