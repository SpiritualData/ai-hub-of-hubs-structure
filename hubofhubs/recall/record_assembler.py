"""RecordContextAssembler: make a person's own records findable by what a message names, with no tool call. Standard library only.

A consumer keeps free-text records (notes, journal lines, tickets) under groupings the assembler does not
index as cards. A message that names a person, a place or a thing ("book Ana for Friday") has no card to
match, yet the record that answers it ("Ana only teaches Tuesday and Thursday evenings") exists. This
assembler takes a ``lister`` the consumer supplies (it returns the records the asker may see), ranks them
against the message by distinctive shared words (inverse document frequency over the listed records, so a
word that appears in most records counts for little) and renders the best few. It reads the user's words
and the stored records only, never a model's output, and calls no model.

Scope: a record MAY carry ``scope_tags`` (see ``scope_tags.py``); a turn carrying ``meta["scope_tags"]``
sees only records whose tags intersect, exactly the cross-arm fence. Never raises.
"""
from __future__ import annotations

import math
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..ports.context import AssembledContext
from .scope_tags import scope_tags_allow

#: Words too common to say what a message is about.
STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would could should may might shall can need to of in on "
    "at by for with about as into from and or but not this that these those i you he she it we they what which who how when where "
    "why all each some any me my your our their him her them us please help can't just want like get make".split())

WORD = re.compile(r"[a-z0-9]+")


def words_of(text: str) -> List[str]:
    """The content words of ``text``: lower-case, three letters or more, not a stopword."""
    return [w for w in WORD.findall(str(text or "").lower()) if len(w) >= 3 and w not in STOPWORDS]


def rank_records(task_text: str, records: Iterable[Dict[str, Any]], *, max_records: int = 3,
                 min_score: float = 1.0) -> List[Tuple[float, Dict[str, Any]]]:
    """The records that share distinctive words with ``task_text``, best first, at most ``max_records``.

    A record's score is the sum of ``log(1 + N / df)`` over the distinct message words it contains (``N`` records, ``df``
    of them containing the word); records scoring under ``min_score`` are dropped, so one very common word never admits a record."""
    rows = [r for r in records if isinstance(r, dict) and str(r.get("text") or "").strip()]
    if not rows:
        return []
    wanted = set(words_of(task_text))
    if not wanted:
        return []
    bags = [set(words_of(f"{r.get('title') or ''} {r.get('text')}")) for r in rows]
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for row, bag in zip(rows, bags):
        score = 0.0
        for word in wanted & bag:
            frequency = sum(1 for other in bags if word in other)
            score += math.log(1 + len(rows) / frequency)
        if score >= min_score:
            scored.append((score, row))
    scored.sort(key=lambda pair: -pair[0])
    return scored[:max_records]


class RecordContextAssembler:
    """A ``ContextAssembler`` over records a consumer lists. ``lister(meta)`` returns dicts with ``id``, ``text`` and optionally
    ``title``, ``when`` and ``scope_tags``; the result is cached for ``cache_seconds`` per ``cache_key(meta)`` so a busy chat
    does not list on every turn. ``header`` is the consumer's one-line description of what the records are."""
    REQUIRES = ()

    def __init__(self, lister: Callable[[Optional[Dict[str, Any]]], Iterable[Dict[str, Any]]], *, header: str = "Records that mention what you asked about:",
                 max_records: int = 3, min_score: float = 1.0, max_chars: int = 600, cache_seconds: float = 60.0,
                 cache_key: Optional[Callable[[Optional[Dict[str, Any]]], str]] = None):
        self.lister, self.header = lister, header
        self.max_records, self.min_score, self.max_chars = max_records, min_score, max_chars
        self.cache_seconds, self.cache_key = cache_seconds, cache_key
        self.cached: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}

    def listed(self, meta: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        key = self.cache_key(meta) if self.cache_key else ""
        hit = self.cached.get(key)
        if hit and time.monotonic() - hit[0] < self.cache_seconds:
            return hit[1]
        rows = [r for r in (self.lister(meta) or []) if isinstance(r, dict)]
        self.cached[key] = (time.monotonic(), rows)
        return rows

    def assemble(self, task_text: str, *, meta: Optional[Dict[str, Any]] = None, on_event: Optional[Any] = None) -> AssembledContext:
        try:
            turn_tags = (meta or {}).get("scope_tags")
            rows = [r for r in self.listed(meta) if scope_tags_allow(r.get("scope_tags"), turn_tags)]
            best = rank_records(task_text, rows, max_records=self.max_records, min_score=self.min_score)
            if not best:
                return AssembledContext()
            lines = []
            for _, row in best:
                label = " ".join(x for x in (str(row.get("title") or "").strip(), f"[{row['when']}]" if row.get("when") else "") if x)
                text = " ".join(str(row["text"]).split())[: self.max_chars]
                lines.append(f"- {label + ': ' if label else ''}{text}")
            ids = [str(row.get("id")) for _, row in best if row.get("id")]
            return AssembledContext(
                context_view=self.header + "\n" + "\n".join(lines), card_ids=ids,
                sources=[{"adapter": "records", "label": "your records", "items": ids}])
        except Exception:  # noqa: BLE001 -- an arm never breaks a turn
            return AssembledContext()

    def record(self, task_text: str, outcome: Dict[str, Any]) -> None:
        return None
