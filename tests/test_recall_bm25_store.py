"""The hub's BM25 content store, run against a small stand-in for the ``bm25s`` library (the real one is the ``bm25`` extra).

The stand-in scores a document by how many query tokens it holds, so these tests pin the store's own behaviour: the walk
(source extensions, size cap, skipped directories), the refresh of only changed files, the parallel multi-query search
with the best score kept per path, the confidence gate, the snippet and the injected skip set and query prompt.
"""
import sys
import types
from pathlib import Path

import pytest


class FakeBM25:
    def index(self, corpus_tokens):
        self.docs = corpus_tokens

    def retrieve(self, query_tokens, corpus, k):
        tokens = set(query_tokens[0])
        scored = sorted(((len(tokens & set(doc)), corpus[i]) for i, doc in enumerate(self.docs)), key=lambda p: -p[0])[:k]
        return [[path for _, path in scored]], [[float(score) for score, _ in scored]]


@pytest.fixture()
def store_class(monkeypatch):
    fake = types.ModuleType("bm25s")
    fake.BM25 = FakeBM25
    fake.tokenize = lambda texts, stopwords=None, stemmer=None: [text.split() for text in texts]
    monkeypatch.setitem(sys.modules, "bm25s", fake)
    from hubofhubs.recall.bm25_store import BM25ContentStore
    return BM25ContentStore


def corpus(tmp_path: Path) -> Path:
    (tmp_path / "alpha.py").write_text("def xfcallback_7q2():\n    return 'legacy_mode'\n")
    (tmp_path / "beta.md").write_text("# Notes\nnothing special here\n")
    (tmp_path / "image.bin").write_bytes(b"xfcallback_7q2")                  # not a source extension
    (tmp_path / "mirror").mkdir()
    (tmp_path / "mirror" / "skipped.py").write_text("xfcallback_7q2 in a skipped folder\n")
    return tmp_path


def test_an_exact_identifier_in_file_content_finds_its_file_with_a_snippet(store_class, tmp_path):
    store = store_class(root=str(corpus(tmp_path)))
    ctx = store.assemble("xfcallback_7q2")
    assert "alpha.py" in ctx.card_ids and "image.bin" not in ctx.card_ids
    assert "BM25 hit: alpha.py" in ctx.context_view and "xfcallback_7q2" in ctx.context_view
    assert ctx.sources == [{"adapter": "bm25", "label": "content match", "items": ctx.card_ids}]


def test_the_consumers_skip_set_replaces_the_default(store_class, tmp_path):
    root = corpus(tmp_path)
    assert "mirror/skipped.py" in store_class(root=str(root)).assemble("xfcallback_7q2").card_ids
    skipping = store_class(root=str(root), skip_dirs=lambda path: {"mirror"})
    assert "mirror/skipped.py" not in skipping.assemble("xfcallback_7q2").card_ids


def test_a_changed_file_is_picked_up_and_a_deleted_one_disappears(store_class, tmp_path):
    root = corpus(tmp_path)
    store = store_class(root=str(root), skip_dirs=lambda path: {"mirror"})
    assert store.assemble("brandnewtoken").card_ids == [] or "beta.md" not in store.assemble("brandnewtoken").card_ids
    (root / "beta.md").write_text("brandnewtoken appears now\n")
    assert store.assemble("brandnewtoken").card_ids[0] == "beta.md"
    (root / "beta.md").unlink()
    assert "beta.md" not in store.assemble("brandnewtoken").card_ids


def test_the_confidence_threshold_drops_weak_hits(store_class, tmp_path):
    root = corpus(tmp_path)
    ctx = store_class(root=str(root), confidence_threshold=3.0, skip_dirs=lambda path: {"mirror"}).assemble("xfcallback_7q2")
    assert ctx.card_ids == []


def test_generated_queries_run_in_parallel_and_the_best_score_per_path_wins(store_class, tmp_path):
    root = corpus(tmp_path)
    asked = []

    class Provider:
        def answer(self, messages, model=None, **kwargs):
            asked.append(messages[-1]["content"])
            return "legacy_mode\n# a comment line\nnotes"

    store = store_class(root=str(root), provider=Provider(), num_queries=2, skip_dirs=lambda path: {"mirror"},
                        query_prompt=lambda n, task: f"own prompt {n}: {task}")
    ctx = store.assemble("something else entirely")
    assert asked == ["own prompt 2: something else entirely"]
    assert set(ctx.card_ids) >= {"alpha.py", "beta.md"} and len(ctx.card_ids) == len(set(ctx.card_ids))


def test_the_default_query_prompt_is_the_standard_text(store_class, tmp_path):
    seen = []

    class Provider:
        def answer(self, messages, model=None, **kwargs):
            seen.append(messages[-1]["content"])
            return ""

    store_class(root=str(corpus(tmp_path)), provider=Provider(), num_queries=3).assemble("find it")
    assert seen[0].startswith("Generate 3 short keyword or phrase queries") and seen[0].endswith("Task: find it")


def test_a_missing_library_raises_with_the_hubs_install_hint(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "bm25s", None)
    from hubofhubs.recall.bm25_store import BM25ContentStore
    with pytest.raises(ImportError, match=r"hubofhubs\[bm25\]"):
        BM25ContentStore(root=str(tmp_path))


def test_an_empty_root_assembles_nothing_and_never_raises(store_class, tmp_path):
    assert store_class(root=str(tmp_path)).assemble("anything").card_ids == []


def test_analyzer_defaults_keep_tokens_and_english_stems_and_drops_stop_words(tmp_path, monkeypatch):
    import sys
    import types
    seen = []

    class Recording(FakeBM25):
        pass

    fake = types.ModuleType("bm25s")
    fake.BM25 = Recording
    fake.tokenize = lambda texts, stopwords=None, stemmer=None: seen.append((stopwords, stemmer)) or [text.split() for text in texts]
    monkeypatch.setitem(sys.modules, "bm25s", fake)
    stemmer_module = types.ModuleType("Stemmer")
    stemmer_module.Stemmer = lambda language: ("stemmer", language)
    monkeypatch.setitem(sys.modules, "Stemmer", stemmer_module)
    from hubofhubs.recall.bm25_store import BM25ContentStore
    (tmp_path / "a.md").write_text("running abstracts\n")
    BM25ContentStore(root=str(tmp_path)).assemble("running")
    assert set(seen) == {(None, None)}
    seen.clear()
    BM25ContentStore(root=str(tmp_path), analyzer="english").assemble("running")
    assert set(seen) == {("en", ("stemmer", "english"))}
    with pytest.raises(ValueError):
        BM25ContentStore(root=str(tmp_path), analyzer="french")
