"""Which harness ran which session, so ``ahohs work --resume <id>`` needs no ``--harness``.

A session id belongs to the harness that ran it, so resuming needs that same harness; a person who never chose one should not have to say it. When a run ends, the id, the harness, the tier
and the folder are written, one line each, to a small file in the hub's own state folder (``private_directory``, on the person's machine, never in a repository). ``--resume <id>`` looks
the harness up; ``--resume last`` is the most recent session recorded for this folder; an explicit ``--harness`` always wins, and a mismatch with what was recorded is said in plain words.
Standard library only.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

STATE_NAME = "hubofhubs-sessions"
FILE_NAME = "sessions.jsonl"
LAST = "last"


class SessionMemory:
    """The sessions recorded for one folder. ``store`` is the folder the file lives in (default: the hub's own state folder; empty when none can be written, and then nothing is kept)."""

    def __init__(self, folder: str, store: Optional[str] = None):
        self.folder = os.path.realpath(folder)
        if store is None:
            from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
            store = private_directory(STATE_NAME) or ""
        self.path = os.path.join(str(store), FILE_NAME) if store else ""

    def rows(self) -> List[Dict[str, Any]]:
        if not self.path or not os.path.exists(self.path):
            return []
        out: List[Dict[str, Any]] = []
        try:
            with open(self.path, encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(row, dict) and row.get("session_id"):
                        out.append(row)
        except OSError:
            return []
        return out

    def record(self, session_id: str, harness: str, tier: str = "") -> bool:
        """Keep that ``session_id`` was run by ``harness`` in this folder (an id recorded again replaces its earlier line). False when nothing could be written."""
        if not self.path or not session_id or not harness:
            return False
        rows = [row for row in self.rows() if row["session_id"] != session_id]
        rows.append({"session_id": session_id, "harness": harness, "tier": tier, "folder": self.folder, "at": time.time()})
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write("".join(json.dumps(row) + "\n" for row in rows[-200:]))
            return True
        except OSError:
            return False

    def find(self, session_id: str) -> Optional[Dict[str, Any]]:
        return next((row for row in reversed(self.rows()) if row["session_id"] == session_id), None)

    def last(self) -> Optional[Dict[str, Any]]:
        """The most recent session recorded for this folder."""
        mine = [row for row in self.rows() if row.get("folder") == self.folder]
        return max(mine, key=lambda row: row.get("at", 0.0)) if mine else None


def resolve_resume(memory: SessionMemory, resume: str, harness: str = "") -> Tuple[str, str, str, str]:
    """``(session id, harness to use, note, error)`` for what the person typed after ``--resume``. ``last`` becomes the most recent session of this folder. The harness is the one recorded with
    the session when ``harness`` (the explicit flag) is empty, else the flag wins; a flag that differs from the recorded one gives a plain ``note``. ``error`` is set when ``last`` has nothing
    to point at. An id nobody recorded is passed on unchanged with no harness (the default is used)."""
    if not resume:
        return "", harness, "", ""
    row = memory.last() if resume == LAST else memory.find(resume)
    if resume == LAST and row is None:
        return "", harness, "", "there is no earlier session in this folder to continue"
    session_id = row["session_id"] if row else resume
    known = str(row.get("harness") or "") if row else ""
    note = ""
    if known and harness and harness != known:
        note = f"That session was run by the {known} harness and you chose {harness}, so it may not continue; leave --harness out to use {known}."
    return session_id, harness or known, note, ""


__all__ = ["LAST", "SessionMemory", "resolve_resume"]
