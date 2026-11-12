"""Warnings folded to one short dim line each, with every full record in a log file.

Python logging used to be copied into a transcript record by record, so a library's chatty warning buried the work. ``NoticeFolder`` is a ``logging.Handler`` that writes every
record in full to a rotated, size-capped file and hands the transcript at most ``SHOWN`` distinct warnings of a run, the first sentence of each, then ONE closing line (after a
quiet second) that counts the rest and says where the details are. An error is never counted away. Records of a library that is not the hub's own (or the consumer's, named in
``own``) reach the file only. A record that says ``in_transcript=False`` goes to the file only. Nothing reads the words of a message to decide whether it matters: only the level,
the logger and that flag. Standard library and the hub only; the screen is reached through two callables, so any screen can use it.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import say
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.text import ellipsize

LINE_CHARS = 400            # the first sentence is not cut to the window: it wraps under its own words on a narrow terminal
SHOWN = 3
SUMMARY_DELAY = 1.0
FILE_BYTES = 1_000_000
FILE_BACKUPS = 2
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
OWN = ("hubofhubs",)


def default_log_path(environ: Optional[Mapping[str, str]] = None) -> Path:
    """Where the full records go when no path is given: the state folder of the person, under ``ahohs``. ``environ`` is the mapping the entry point handed in (the hub's modules never read
    the process environment themselves; ``tests/test_no_environment.py``); without one the person's home folder is used."""
    env = environ if environ is not None else {}
    base = Path(env.get("XDG_STATE_HOME") or (Path(env.get("HOME") or Path.home()) / ".local" / "state"))
    return base / "ahohs" / "session.log"


def short_text(message: str, limit: int = LINE_CHARS) -> str:
    """The first sentence of a message on one line: a trailing parenthesis goes first when it is too long, then a whole clause, then a word boundary and an ellipsis."""
    lines = [line for line in str(message).splitlines() if line.strip()]
    first = " ".join(lines[0].split()) if lines else ""
    end = re.search(r"[.!?](?=\s|$)", first)
    if end:
        first = first[:end.start()]
    first = first.strip()
    if len(first) > limit:
        first = re.sub(r"\s*\([^()]*\)$", "", first)
    if len(first) <= limit:
        return first
    clause = max(first.rfind(sep, 0, limit) for sep in (";", ":"))
    if clause >= limit * 0.6:
        return first[:clause].rstrip() + "…"
    return ellipsize(first, limit)


class Quiet(RotatingFileHandler):
    """A rotating log file whose own failures (a full disk, an unwritable folder) never reach the screen."""

    def handleError(self, record: logging.LogRecord) -> None:
        pass


def open_log(path: Path) -> Optional[logging.Handler]:
    """The capped log file handler for ``path``, or None when its folder cannot be made. Never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = Quiet(path, maxBytes=FILE_BYTES, backupCount=FILE_BACKUPS, encoding="utf-8", delay=True)
    except Exception:  # noqa: BLE001
        return None
    handler.setFormatter(logging.Formatter(FORMAT))
    return handler


class NoticeFolder(logging.Handler):
    """Routes logging for the screen: the full record to a file, a short line to ``write`` (called from any thread; it must be thread-safe)."""

    def __init__(self, write: Callable[[str], None], schedule: Optional[Callable[[float, Callable[[], None]], None]] = None, *, verbosity: int = 0,
                 log_path: Optional[Path] = None, own: Sequence[str] = OWN, environ: Optional[Mapping[str, str]] = None):
        super().__init__()
        self.write, self.schedule, self.verbosity, self.own = write, schedule, verbosity, tuple(own)
        self.log_path = Path(log_path) if log_path is not None else default_log_path(environ)
        self.file_handler = open_log(self.log_path)
        self.seen: Dict[str, int] = {}
        self.errors_seen: Dict[str, int] = {}
        self.lines_shown = 0
        self.more = 0
        self.burst_open = False
        self.lock = threading.RLock()
        self.setFormatter(logging.Formatter(FORMAT))

    def close(self) -> None:
        if self.file_handler is not None:
            self.file_handler.close()
        super().close()

    def begin_run(self) -> None:
        """A run starts: close the group so far and count afresh."""
        self.finish()
        with self.lock:
            self.seen, self.errors_seen, self.lines_shown, self.more = {}, {}, 0, 0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self.file_handler is not None:
                self.file_handler.handle(record)
            lines = self.lines_for(record)
            for line in lines:
                self.write(line)
            if self.verbosity < 1 and self.burst_open and self.schedule is not None:
                self.schedule(SUMMARY_DELAY, self.finish)
        except Exception:  # noqa: BLE001 -- a logging problem never reaches the screen; the file already has the record
            pass

    def lines_for(self, record: logging.LogRecord) -> List[str]:
        if self.verbosity >= 1:
            return [self.format(record)]
        if getattr(record, "in_transcript", True) is False:
            return []
        error = record.levelno >= logging.ERROR
        if not error and not record.name.startswith(self.own):
            return []
        short = short_text(record.getMessage())
        if not short:
            return []
        with self.lock:
            if error:
                if short in self.errors_seen:
                    self.errors_seen[short] += 1
                    return []
                self.errors_seen[short] = 1
                self.burst_open = True
                return [say("polished.notice.line", text=short)]
            if short in self.seen:
                self.seen[short] += 1
                return []
            self.seen[short] = 1
            self.burst_open = True
            if self.lines_shown >= SHOWN:
                self.more += 1
                return []
            self.lines_shown += 1
        return [say("polished.notice.line", text=short)]

    def where(self) -> str:
        if self.file_handler is None:
            return ""
        shown = str(self.log_path)
        home = str(Path.home())
        return "~" + shown[len(home):] if shown.startswith(home + os.sep) else shown

    def finish(self) -> bool:
        """Close the group of notices with one line: how many more there were and where the details are. Once per burst, after the lines it closes."""
        with self.lock:
            if not self.burst_open or self.verbosity >= 1:
                return False
            self.burst_open = False
            more, self.more = self.more, 0
        where = self.where()
        if not where:
            self.write(say("polished.notice.detailsVerbose"))
        elif more:
            self.write(say("polished.notice.more", count=more, where=where))
        else:
            self.write(say("polished.notice.details", where=where))
        return True


__all__ = ["NoticeFolder", "default_log_path", "open_log", "short_text"]
