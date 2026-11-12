"""The arms of Focus Context: what a session is told before it starts.

* ``no_context``: nothing (a session as it was, the helper searches the files for the request's words on its own).
* ``filesystem_search``: the floor that models that search, made visible: every note ranked by how often the request's words occur in it, the focus ignored, the top
  ones named. It is what a helper finds by searching for the word.
* ``configured_focus_context``: the notes of the sources the person configured, the named focus first (soft affinity, ranking only), the scope fence kept, through the
  Context Retriever's ``focus_first`` arm; then the brief and the one line.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from esoi import implementation

from hubofhubs.the_intelligence.subconscious.focus_context.brief import FocusContext, context_of
from hubofhubs.the_intelligence.subconscious.focus_context.notes import Note, focus_tag, note_of


def notes_of(raw: Sequence[Any]) -> list:
    """The notes of a list of ``Note`` or mappings (a mapping without words is left out)."""
    found = [item if isinstance(item, Note) else note_of(item, fallback_id=f"note-{number}") for number, item in enumerate(raw, 1)]
    return [note for note in found if note is not None]


@implementation("focus-context", "no_context")
class NoContext:
    """Nothing is gathered: the session starts with the goal alone."""
    REQUIRES = ()

    def gather(self, request: str, notes: Sequence[Mapping[str, Any]], focus: str = "", max_notes: int = 5, budget_tokens: int = 1500, scope: Sequence[str] = ()) -> FocusContext:
        return FocusContext(focus=focus)


@implementation("focus-context", "filesystem_search")
class FilesystemSearch:
    """The request's words searched for in every note, the focus and the fence ignored (what a helper does when it greps for the word)."""
    REQUIRES = ()

    def gather(self, request: str, notes: Sequence[Mapping[str, Any]], focus: str = "", max_notes: int = 5, budget_tokens: int = 1500, scope: Sequence[str] = ()) -> FocusContext:
        from hubofhubs.the_intelligence.subconscious.context_retriever.units import tokens
        terms = set(tokens(request))
        scored = []
        for note in notes_of(notes):
            words = tokens(note.body())
            hits = sum(1 for word in words if word in terms)
            if hits:
                scored.append((-hits, note.id, note))
        return context_of(focus, [note for _, _, note in sorted(scored)[:max_notes]])


@implementation("focus-context", "configured_focus_context")
class ConfiguredFocusContext:
    """The notes of the configured sources, the named focus first, the scope fence kept, then the brief and the line."""
    REQUIRES = ()

    def gather(self, request: str, notes: Sequence[Mapping[str, Any]], focus: str = "", max_notes: int = 5, budget_tokens: int = 1500, scope: Sequence[str] = ()) -> FocusContext:
        from hubofhubs.the_intelligence.subconscious.context_retriever.focus_first import FocusFirst
        held = {note.id: note for note in notes_of(notes)}
        if not held:
            return FocusContext(focus=focus)
        meta = {note.id: {"affinity_tags": list(note.affinity_tags), "scope_tags": list(note.scope_tags), "overview": note.overview, "timestamp": note.timestamp} for note in held.values()}
        asked = {"affinity_tags": [focus_tag(focus)] if focus else [], "scope_tags": list(scope)}
        hits = FocusFirst().retrieve(request, {ident: note.body() for ident, note in held.items()}, budget_tokens=budget_tokens, meta=meta, request=asked)
        chosen: list = []
        for hit in hits:
            if hit.file in held and held[hit.file] not in chosen:
                chosen.append(held[hit.file])
        return context_of(focus, chosen[:max_notes])
