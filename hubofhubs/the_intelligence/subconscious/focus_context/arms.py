"""The arms of Focus Context: what a session is told before it starts.

* ``no_context``: nothing (a session as it was, the helper searches the files for the request's words on its own).
* ``filesystem_search``: the floor that models that search, made visible: every note ranked by how often the request's words occur in it, the focus ignored, the top
  ones named. It is what a helper finds by searching for the word.
* ``configured_focus_context``: the notes of the sources the person configured, the named focus first (soft affinity, ranking only), the scope fence kept, through the
  Context Retriever's ``focus_first`` arm; then the brief and the one line. Its word-count floor is the gate here (the baseline).
* ``llm_judged_focus_context``: the same ranking, made generous, only proposes candidates; a fast-tier judge (``judge.py``) decides which bear on the request, and only those
  reach the brief. No judge answer, nothing added.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from esoi import implementation

from hubofhubs.the_self.assembler import arm_needs as needs

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


@implementation("focus-context", "llm_judged_focus_context")
class LlmJudgedFocusContext:
    """Candidates ranked by words and affinity (generous, no floor), relevance decided by a fast-tier judge that reviews them top down in small pages and stops when a page
    holds nothing relevant: only the notes the judge names reach the brief; a broken judge adds nothing."""
    REQUIRES = (needs.CLAUDE_BINARY, needs.CLAUDE_ACCOUNT, needs.CLAUDE_CLI_BOUNDARY)
    PAID = True      # every gathering with candidates calls a model: never run by a free (offline) metric run

    def __init__(self, ask=None, tier: str = "fast"):
        from hubofhubs.the_intelligence.subconscious.focus_context.judge import RelevanceJudge
        self.judge = RelevanceJudge(ask, tier)
        self.failure = ""
        self.review = {"pages": 0, "reviewed": 0, "calls": 0}      # what the last gathering showed the judge, for a caller that records it

    def candidates(self, request: str, held: dict, focus: str, scope: Sequence[str], budget_tokens: int) -> list:
        """Every in-scope note worth showing the judge, best first. The order is words (BM25F score, doubled for a note at home in the focus), then the focus's overview, then the
        rest of the focus's notes newest first. It is ordering and recall only; the scope fence is kept; nothing here decides relevance."""
        from hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.scope_tags import scope_tags_allow
        from hubofhubs.the_intelligence.subconscious.context_retriever.focus_first import FocusFirst
        meta = {n.id: {"affinity_tags": list(n.affinity_tags), "scope_tags": list(n.scope_tags), "overview": n.overview, "timestamp": n.timestamp} for n in held.values()}
        asked = {"affinity_tags": [focus_tag(focus)] if focus else [], "scope_tags": list(scope)}
        ranker = FocusFirst()
        ranker.FLOOR = False
        hits = ranker.retrieve(request, {ident: n.body() for ident, n in held.items()}, budget_tokens=10 ** 9, meta=meta, request=asked)
        home = focus_tag(focus)
        seen, scored, rest = set(), [], []
        for position, hit in enumerate(hits):
            note = held.get(hit.file)
            if note is None or note.id in seen:
                continue
            seen.add(note.id)
            (scored if hit.score > 0 else rest).append((-hit.score * (2.0 if home and home in note.affinity_tags else 1.0), position, note))
        ordered = [n for _, _, n in sorted(scored, key=lambda row: (row[0], row[1]))] + [n for _, _, n in rest]
        newest = sorted((n for n in held.values() if n.id not in seen and home and home in n.affinity_tags and scope_tags_allow(list(n.scope_tags), list(scope))),
                        key=lambda n: n.timestamp, reverse=True)
        return ordered + newest

    def gather(self, request: str, notes: Sequence[Mapping[str, Any]], focus: str = "", max_notes: int = 5, budget_tokens: int = 1500, scope: Sequence[str] = ()) -> FocusContext:
        held = {note.id: note for note in notes_of(notes)}
        self.failure = ""
        self.review = {"pages": 0, "reviewed": 0, "calls": 0}
        if not held:
            return FocusContext(focus=focus)
        pool = self.candidates(request, held, focus, scope, budget_tokens)
        if not pool:
            return FocusContext(focus=focus)
        verdict = self.judge.judge(request, pool, focus)
        self.failure = verdict.failure
        self.review = {"pages": verdict.pages, "reviewed": verdict.reviewed, "calls": verdict.calls}
        return context_of(focus, [pool[n - 1] for n in verdict.numbers][:max_notes])
