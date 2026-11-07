"""Machine paths never reach the reader: a folder this deployment works in is shown relative to it.

A worker that reads and writes files names them by absolute path, and a final reply carried the folder of a run in front of every name. The reader cannot use a server's folder layout and
it tells them nothing about the machine they should not see. The roots to hide are CONFIGURATION (the consumer's list of private roots,
filled by the consumer from the folders it works in), so this reads no wording of the reply: it replaces a known prefix, the way the
em dash pass replaces a known character. A file the worker wrote stays identifiable by its relative name.
"""
from __future__ import annotations

from typing import Any, Iterable, List


def clean_roots(roots: Iterable[Any]) -> List[str]:
    """The roots worth hiding: absolute, at least two path parts deep (never ``/`` or ``/tmp`` alone), longest first."""
    out = {str(r).rstrip("/") for r in roots if isinstance(r, str) and str(r).startswith("/")}
    return sorted((r for r in out if len([p for p in r.split("/") if p]) >= 2), key=len, reverse=True)


def relativize(text: Any, roots: Iterable[Any]) -> Any:
    """``text`` with each root shown relative to itself (``<root>/a/b`` -> ``a/b``); a bare root becomes ``the working folder``."""
    if not isinstance(text, str) or not text:
        return text
    for root in clean_roots(roots):
        text = text.replace(root + "/", "").replace(root, "the working folder")
    return text
