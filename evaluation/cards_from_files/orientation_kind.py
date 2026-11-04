"""The orientation kind of case: does the view put a reader in the part of the code the task is about?

A free proxy with no model. The cases are the file-finding tasks, and a case asks for the neighbourhood of the target file instead of
the file. It is right (``raw``) when one of the first three files of the view is in the target's own folder (``folder_hit``). ``area_hit``
records whether the first card's files have a common folder that is the target's folder or its parent (never the root, which every card
of spread files would reach). It measures nearness, not that a reader found the file, and a card per file favours it, which is why it is
a minor part of the mix (``mix.py``).
"""
from __future__ import annotations

import posixpath

FIRST = 3


def common_folder(paths):
    folders = [posixpath.dirname(p) for p in paths]
    return posixpath.commonpath(folders) if folders and all(folders) else ""


def area_hit(card, folder):
    here = common_folder(card)
    return bool(here) and (here == folder or here == posixpath.dirname(folder))


def judge(got, case):
    view, folder = list(dict.fromkeys(got["view"])), posixpath.dirname(case["target"])
    folder_hit = any(posixpath.dirname(path) == folder for path in view[:FIRST])
    first_card = got["cards"][0] if got.get("cards") else []
    return dict(raw=folder_hit, folder_hit=folder_hit, area_hit=area_hit(first_card, folder),
                got="folder hit" if folder_hit else "no file of the folder in the first three", note=f"{folder or 'root'} <- {view[0] if view else 'nothing'}")
