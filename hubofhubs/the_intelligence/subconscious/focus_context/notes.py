"""A saved note: the one shape every source of context is read into, whatever it came from (a folder of saved cards, a folder of text files, a program's output or a
consumer's own provider function)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.scope_tags import as_tag_list

FOCUS_KIND = "focus"          # a focus is the tag ``focus:<name>`` in the affinity vocabulary (``affinity_tags``)
EXCERPT_CHARS = 1200          # one note costs the brief at most this many characters, so a long file cannot crowd out the rest


def focus_tag(focus: str) -> str:
    """The affinity tag of a named focus (``""`` for no focus)."""
    return f"{FOCUS_KIND}:{focus.strip()}" if focus and focus.strip() else ""


@dataclass(frozen=True)
class Note:
    """One saved piece of what is known: ``id``, a short ``title``, its ``text`` (an excerpt), the groupings it is at home in (``affinity_tags``, soft: ranking only),
    who may see it (``scope_tags``, a hard fence), whether it is an ``overview`` of its focus (always offered, short) and when it was written (``timestamp``)."""
    id: str
    title: str
    text: str
    affinity_tags: Tuple[str, ...] = ()
    scope_tags: Tuple[str, ...] = ()
    overview: bool = False
    timestamp: str = ""

    def body(self) -> str:
        return f"{self.title}\n{self.text}".strip()


def flat_text(value: Any) -> str:
    """The words of a saved value: a string as it is, a list or mapping by its parts (a card's content may be either)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return " ".join(part for part in (flat_text(v) for v in value.values()) if part)
    if isinstance(value, (list, tuple)):
        return " ".join(part for part in (flat_text(v) for v in value) if part)
    return str(value)


def note_of(raw: Mapping[str, Any], default_focus: str = "", fallback_id: str = "") -> Optional[Note]:
    """A note from a mapping with the usual card fields (``id``, ``name`` or ``title``, ``summary``, ``description``, ``text`` or ``content``, ``affinity_tags``,
    ``scope_tags``, ``overview``, ``timestamp``); None when it carries no words. A note with no home of its own takes ``default_focus`` (the focus its source names)."""
    if not isinstance(raw, Mapping):
        return None
    ident = str(raw.get("id") or fallback_id or "").strip()
    title = flat_text(raw.get("title") or raw.get("name"))
    parts = [flat_text(raw.get(key)) for key in ("summary", "description", "text", "content")]
    text = " ".join(dict.fromkeys(part for part in parts if part))
    if not ident or not (title or text):
        return None
    tags = as_tag_list(raw.get("affinity_tags")) or ([focus_tag(default_focus)] if default_focus else [])
    stamp = str(raw.get("timestamp") or raw.get("updated_at") or raw.get("created_at") or "")
    return Note(id=ident, title=title[:160] or ident, text=text[:EXCERPT_CHARS], affinity_tags=tuple(tags), scope_tags=tuple(as_tag_list(raw.get("scope_tags"))),
                overview=bool(raw.get("overview")), timestamp=stamp)


def notes_from_json(text: str, default_focus: str = "") -> Tuple[Note, ...]:
    """The notes of a JSON document: one mapping, or a list of them (what a program prints); an unreadable document is no notes."""
    try:
        data = json.loads(text)
    except ValueError:
        return ()
    items = data if isinstance(data, list) else [data]
    found = (note_of(item, default_focus, fallback_id=f"note-{number}") for number, item in enumerate(items, 1))
    return tuple(note for note in found if note is not None)
