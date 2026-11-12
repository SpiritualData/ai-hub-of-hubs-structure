"""Reading a file the vendored screen shows, standard library only. Modified from upstream (Mistral Vibe v2.26.1, Apache-2.0, vibe/utils/io.py): cut to the two readers the screen
calls (the diff renderer and the plan-file message), the encoding guess dropped (UTF-8 with replacement), no lock or atomic-write helpers."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import NamedTuple


class ReadSafeResult(NamedTuple):
    r"""Text read from a file with ``\n`` line endings, the codec used and the newline style the file had."""

    text: str
    encoding: str
    newline: str = os.linesep


def read_safe(path: Path, *, raise_on_error: bool = False) -> ReadSafeResult:
    """The text of ``path``; a file that cannot be read gives empty text unless ``raise_on_error``."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        if raise_on_error:
            raise
        return ReadSafeResult("", "utf-8")
    text = raw.decode("utf-8", errors="replace")
    newline = "\r\n" if "\r\n" in text else ("\r" if "\r" in text and "\n" not in text else "\n")
    return ReadSafeResult(text.replace("\r\n", "\n").replace("\r", "\n"), "utf-8", newline)


async def read_safe_async(path: Path, *, raise_on_error: bool = False) -> ReadSafeResult:
    """``read_safe`` off the event loop."""
    return await asyncio.to_thread(read_safe, path, raise_on_error=raise_on_error)
