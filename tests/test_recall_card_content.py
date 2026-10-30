"""Offline tests for the source-agnostic card CONTENT model (hubofhubs.recall): the reference-resolver registry and its
built-ins, content normalisation, recency ranking and the dedupe of references. Stub resolvers only, no network."""
from __future__ import annotations

from typing import Any, Dict

from hubofhubs.recall.card_content_render import (
    content_identity_key,
    dedupe_content,
    normalize_content as _normalize_content,
    rank_content_by_recency_relevance as _rank_content_by_recency_relevance,
)
from hubofhubs.recall.reference_resolver import (
    NoteResolver,
    ReferenceResolver,
    build_resolver_registry,
    _render_unresolved,
)


class _StubCollectionResolver:
    """A stub ``collection`` resolver that returns FRESH text injected at assemble time.

    Tracks calls so a test can assert the reference was resolved live (not a stale snapshot).
    """

    def __init__(self, text: str = "FRESH_COLLECTION_ROWS") -> None:
        self.text = text
        self.calls: list = []

    def resolve(self, locator: Dict[str, Any], *, max_chars: int = 2000) -> str:
        self.calls.append(locator)
        return f"{self.text} for {locator.get('name', '?')}"


def _content_card(card_id: str, *, keywords, summary="", content, files=None) -> Dict[str, Any]:
    return {
        "id": card_id,
        "keywords": keywords,
        "summary": summary,
        "files": files or [],
        "content": content,
        "conventions": [],
        "provenance": {"created_by_task": "", "model": "", "created_at": "",
                       "last_verified_at": ""},
        "usage_count": 0,
        "last_outcome": "unknown",
    }


# ---------------------------------------------------------------------------
# ReferenceResolver registry + built-ins
# ---------------------------------------------------------------------------

class TestResolverRegistry:
    def test_note_resolver_returns_text(self):
        assert NoteResolver().resolve({"text": "hello"}) == "hello"

    def test_note_resolver_truncates(self):
        out = NoteResolver().resolve({"text": "x" * 100}, max_chars=10)
        assert len(out) <= 10
        assert out.endswith("…")

    def test_note_resolver_never_raises_on_bad_locator(self):
        assert NoteResolver().resolve(None) == ""  # type: ignore[arg-type]
        assert NoteResolver().resolve({}) == ""

    def test_build_registry_has_note_builtin(self):
        reg = build_resolver_registry()
        assert "note" in reg
        assert isinstance(reg["note"], ReferenceResolver)

    def test_build_registry_wires_file_when_reader_given(self):
        reg = build_resolver_registry(file_read_text=lambda p, n: "content")
        assert "file" in reg
        assert reg["file"].resolve({"path": "x"}) == "content"

    def test_consumer_resolver_wins_on_collision(self):
        custom = _StubCollectionResolver()
        reg = build_resolver_registry(consumer_resolvers={"note": custom})
        assert reg["note"] is custom

    def test_unresolved_pointer_lines(self):
        assert "unresolved" in _render_unresolved("collection", {"name": "x", "id": "y"})
        assert "unresolved" in _render_unresolved("conversation", {"conv_id": "c1"})
        assert "unresolved" in _render_unresolved("query", {"query": "find x"})

    def test_unresolved_never_raises(self):
        assert _render_unresolved("collection", None) != ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Content normalization / recency ranking / trim
# ---------------------------------------------------------------------------

class TestContentHelpers:
    def test_normalize_drops_non_dicts_and_defaults(self):
        out = _normalize_content([{"type": "note", "locator": {"text": "a"}}, "junk", 5])
        assert len(out) == 1
        assert out[0]["type"] == "note"
        assert out[0]["ts"] == 0.0
        assert out[0]["id"]  # synthesized

    def test_normalize_missing_content_is_empty(self):
        assert _normalize_content(None) == []
        assert _normalize_content("not a list") == []

    def test_rank_prefers_relevance_then_recency(self):
        items = [
            {"id": "old_rel", "type": "note", "locator": {"text": "alpha topic"}, "ts": 1.0,
             "why": "alpha"},
            {"id": "new_irrel", "type": "note", "locator": {"text": "zeta unrelated"}, "ts": 100.0,
             "why": "zeta"},
        ]
        ranked = _rank_content_by_recency_relevance(items, {"alpha"}, limit=2)
        assert ranked[0]["id"] == "old_rel"  # relevance beats raw recency

    def test_rank_limit_caps(self):
        items = [{"id": f"n{i}", "type": "note", "locator": {"text": "x"}, "ts": float(i),
                  "why": ""} for i in range(10)]
        assert len(_rank_content_by_recency_relevance(items, set(), limit=3)) == 3


# ---------------------------------------------------------------------------
# Reference DEDUP on write: re-adding the same collection id / file path / note
# merges into the existing item (newest ts + freshest why) instead of bloating.
# ---------------------------------------------------------------------------

class TestContentDedup:
    def test_identity_key_by_locator(self):
        # collection -> id; file -> path; note -> text; case/space-insensitive.
        assert content_identity_key(
            {"type": "collection", "locator": {"id": "COL-1", "name": "Pricing"}}
        ) == content_identity_key(
            {"type": "collection", "locator": {"id": "col-1", "name": "Other"}}
        )
        assert content_identity_key({"type": "file", "locator": {"path": "a/b.py"}}) \
            == content_identity_key({"type": "file", "locator": {"path": "a/b.py"}})
        # different collections do NOT collapse
        assert content_identity_key({"type": "collection", "locator": {"id": "x"}}) \
            != content_identity_key({"type": "collection", "locator": {"id": "y"}})

    def test_dedupe_keeps_first_id_newest_ts_freshest_why(self):
        items = [
            {"id": "keep", "type": "collection", "locator": {"id": "c1"}, "ts": 10.0, "why": "old"},
            {"id": "dropme", "type": "collection", "locator": {"id": "c1"}, "ts": 20.0, "why": "new"},
        ]
        out = dedupe_content(items)
        assert len(out) == 1
        assert out[0]["id"] == "keep"          # first occurrence's stable id wins
        assert out[0]["ts"] == 20.0            # refreshed to the newest
        assert out[0]["why"] == "new"          # freshest non-empty why

    def test_dedupe_preserves_distinct_refs_and_order(self):
        items = [
            {"id": "a", "type": "file", "locator": {"path": "a.py"}, "ts": 1.0, "why": ""},
            {"id": "b", "type": "file", "locator": {"path": "b.py"}, "ts": 1.0, "why": ""},
            {"id": "a2", "type": "file", "locator": {"path": "a.py"}, "ts": 2.0, "why": "x"},
        ]
        out = dedupe_content(items)
        assert [it["id"] for it in out] == ["a", "b"]
        assert out[0]["ts"] == 2.0 and out[0]["why"] == "x"
