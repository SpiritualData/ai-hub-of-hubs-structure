"""Counts what a card builder reads from the sources while it bootstraps or refreshes the store (the cost of reading, apart from the cost of the
cards): file opens, distinct files and bytes under the corpus root, seen through the interpreter's audit hook so no builder has to cooperate.

Bootstrapping a store from the sources is the card builder's job (this component), not the retrieval arm's: an arm only builds the index it derives
from the cards. The reads here are what a consumer whose sources are remote would pay for at each (re)build: ``reads_per_item`` is the opens per file
ingested, and a refresh that re-reads every file is a full rescan (``refresh_share`` 1.0) while an incremental builder reads a small share.
"""
from __future__ import annotations

import os
import sys

_STATE = {"root": None, "opens": 0, "files": set(), "bytes": 0}


def _hook(event, args):
    root = _STATE["root"]
    if root is None or event != "open" or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    mode = args[1] if len(args) > 1 else None
    if mode is not None and ("w" in str(mode) or "a" in str(mode) or "x" in str(mode)):
        return
    try:
        path = os.fsdecode(args[0])
    except (TypeError, ValueError):
        return
    if path.startswith(root) and os.path.isfile(path):
        _STATE["opens"] += 1
        _STATE["files"].add(path)
        try:
            _STATE["bytes"] += os.path.getsize(path)
        except OSError:
            pass


sys.addaudithook(_hook)


class Reads:
    """``with Reads(root) as r: ...`` then ``r.opens``, ``r.files`` (distinct) and ``r.bytes`` of the reads under ``root``."""

    def __init__(self, root):
        self.root = str(root).rstrip("/") + "/"
        self.opens = self.files = self.bytes = 0

    def __enter__(self):
        _STATE.update(root=self.root, opens=0, files=set(), bytes=0)
        return self

    def __exit__(self, *exc):
        self.opens, self.files, self.bytes = _STATE["opens"], len(_STATE["files"]), _STATE["bytes"]
        _STATE["root"] = None
        return False
