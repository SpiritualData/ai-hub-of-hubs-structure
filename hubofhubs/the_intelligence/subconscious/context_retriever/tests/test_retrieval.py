"""The retrieval units, the lexical arms and the budgeted choice, on a tiny corpus: no model, no network."""
from hubofhubs.the_intelligence.subconscious.context_retriever.base import within_budget
from hubofhubs.the_intelligence.subconscious.context_retriever.lexical import Bm25Body, Bm25Fielded, Bm25WholeFiles
from hubofhubs.the_intelligence.subconscious.context_retriever.units import build_corpus, cochange_counts, import_links, python_pieces, tokens

NET = '"""Network helpers."""\nimport time\n\n\ndef retry_delay(attempt):\n    """How long to wait before the next retry."""\n    return 2 ** attempt\n\n\ndef open_socket(host):\n    return host\n'
UI = '"""Drawing."""\nfrom net import retry_delay\n\n\ndef draw_window(title):\n    """Draw the main window."""\n    return title\n'
FILES = {"net.py": NET, "ui.py": UI, "notes.md": "# Notes\n\nThe retry delay doubles each attempt.\n\n# Colours\n\nBlue and green.\n"}


def test_tokens_split_identifiers_and_stem():
    assert {"retry", "delay"} <= set(tokens("retryDelay retry_delay retries"))
    assert "the" not in tokens("the delay")


def test_python_is_cut_into_a_header_and_one_unit_per_definition():
    pieces = python_pieces(NET)
    assert [p[3] for p in pieces] == [True, False, False]
    assert "retry_delay" in pieces[1][2] and "How long" in pieces[1][2]


def test_import_links_run_both_ways():
    links = import_links(FILES)
    assert links["ui.py"] == {"net.py"} and links["net.py"] == {"ui.py"}


def test_cochange_shares_a_commit_among_its_pairs():
    counts = cochange_counts([{"files": ["a.py", "b.py", "c.py"]}], {"a.py", "b.py", "c.py"})
    assert counts["a.py"]["b.py"] == 0.5


def test_fielded_bm25_finds_the_function_by_its_name_and_prose():
    arm = Bm25Fielded()
    hits = arm.retrieve("how long is the retry delay", FILES, budget_tokens=4000)
    assert hits and hits[0].file in ("net.py", "notes.md") and "net.py" in [h.file for h in hits]


def test_a_budget_skips_a_unit_that_does_not_fit_and_keeps_a_smaller_one():
    corpus = build_corpus(FILES)
    ranked = [(i, 1.0 / (i + 1)) for i in range(len(corpus.units))]
    smallest = min(u.tokens for u in corpus.units)
    hits = within_budget(corpus, ranked, smallest)
    assert hits and sum(h.tokens for h in hits) <= smallest


def test_whole_files_use_one_unit_per_file_and_body_arm_has_no_fields_but_the_text():
    arm = Bm25WholeFiles()
    arm.prepare(FILES)
    assert len(arm.corpus.units) == len(FILES)
    body = Bm25Body()
    body.prepare(FILES)
    assert list(body.indexes) == ["body"]


def test_the_mix_is_set_by_the_pinned_file_cases():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "evaluation"))
    from context_retrieval import mix
    assert mix.counts(dict(file=63, topic=150, orientation=63, none=48)) == dict(file=63, topic=126, orientation=32, none=32)


def test_the_corpus_cache_defaults_to_a_private_folder_and_is_written_whole(tmp_path, monkeypatch):
    import os
    import tempfile
    from hubofhubs.the_intelligence.subconscious.context_retriever import units
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    files = {"a.md": "# Title\n\nsome words about caching\n"}
    first = units.cached_corpus(files)
    folder = tmp_path / f"{units.CACHE_FOLDER}-{os.getuid()}"
    assert [p.suffix for p in folder.iterdir()] == [".pkl"]                  # in this account's folder, no partial file left
    assert not (tmp_path / units.CACHE_FOLDER).exists()                      # never the shared name
    assert units.cached_corpus(files).digest == first.digest
    os.chmod(folder, 0o777)                                                  # a folder others can write is not read from
    import pickle
    monkeypatch.setattr(pickle, "loads", lambda data: (_ for _ in ()).throw(AssertionError("read an unsafe cache")))
    assert units.cached_corpus(files).digest == first.digest
