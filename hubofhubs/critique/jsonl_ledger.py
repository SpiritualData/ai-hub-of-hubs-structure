"""The folder a keyed JSON-lines ledger is kept in. The file-per-key store itself is esoi's ``RunFiles``
(``esoi.metric_results``): a tool-call ledger and a metric ledger both use it, because both are records "kept by the runner and
never by a model", written by two processes at once (the brain, and a worker's shell command). This module adds only where
such a ledger lives."""
from __future__ import annotations

import os
import tempfile


def default_directory(name: str) -> str:
    """The ledger directory used when none is configured: ``<temp>/<name>``, shared by the accounts on the machine.

    That shared folder belongs to whichever account made it first (mode 0775, so only its group may write), and an
    account outside the group then could not record anything: every metric result of a deep run on a second account's
    lane came back "could not be written". When this account cannot write the shared folder, it gets its own
    (``<name>-<uid>``). Both ends of a run (the brain and the worker's shell) are the same account, so both pick the
    same folder.
    """
    shared = os.path.join(tempfile.gettempdir(), name)
    if not hasattr(os, "getuid"):
        return shared
    if os.path.isdir(shared):
        usable = os.access(shared, os.W_OK | os.X_OK)
    else:
        usable = os.access(tempfile.gettempdir(), os.W_OK | os.X_OK)
    return shared if usable else f"{shared}-{os.getuid()}"
