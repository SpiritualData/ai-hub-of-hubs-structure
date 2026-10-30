"""The folder review decides what is not worth indexing; its settings are arguments and it names no consumer folder."""
from pathlib import Path

from hubofhubs.recall.context_folder_review import folder_review, nested_vcs_dirs, review_corpus


def make_corpus(root: Path, store_dir_name: str) -> Path:
    for i in range(4):
        (root / "app" / f"m{i}.py").parent.mkdir(parents=True, exist_ok=True)
        (root / "app" / f"m{i}.py").write_text(f"x = {i}\n")
    (root / "dep" / ".git").mkdir(parents=True)
    (root / "dep" / "lib.py").write_text("y = 1\n")
    (root / "owned" / ".git").mkdir(parents=True)
    (root / "owned" / store_dir_name).mkdir()
    (root / "owned" / store_dir_name / "bootstrap_meta.json").write_text("{}")
    (root / "owned" / "mine.py").write_text("z = 1\n")
    return root


class Silent:
    def request(self, *args, **kwargs):
        raise AssertionError("no model call is expected below the file-count floor")


def test_nested_repositories_are_found_by_their_markers(tmp_path):
    corpus = make_corpus(tmp_path, ".cards")
    assert set(nested_vcs_dirs(corpus, set())) == {"dep", "owned"}


def test_an_unreviewable_corpus_is_indexed_in_full(tmp_path):
    corpus = make_corpus(tmp_path, ".cards")
    assert folder_review(corpus, set(), Silent(), None, tmp_path / "cards", store_dir_name=".cards") == set()


def test_the_consumers_store_folder_name_decides_whether_a_nested_repo_has_its_own_store(tmp_path, monkeypatch):
    import hubofhubs.recall.context_folder_review as review
    monkeypatch.setattr(review, "FOLDER_REVIEW_MIN_FILES", 1)
    corpus = make_corpus(tmp_path, ".cards")
    excluded, verdicts = review_corpus(corpus, set(), None, None, tmp_path / "cards1", store_dir_name=".cards")
    assert {"dep", "owned"} <= excluded
    assert "its own card store is imported instead" in verdicts["owned"]["reason"]
    assert "its own card store is imported instead" not in verdicts["dep"]["reason"]
    _, other = review_corpus(corpus, set(), None, None, tmp_path / "cards2", store_dir_name=".elsewhere")
    assert "its own card store is imported instead" not in other["owned"]["reason"]


def test_nested_repositories_are_indexed_when_the_consumer_switches_the_safeguard_off(tmp_path, monkeypatch):
    import hubofhubs.recall.context_folder_review as review
    monkeypatch.setattr(review, "FOLDER_REVIEW_MIN_FILES", 1)
    corpus = make_corpus(tmp_path, ".cards")
    excluded, _ = review_corpus(corpus, set(), None, None, tmp_path / "cards", store_dir_name=".cards", skip_nested_repos=False)
    assert "dep" not in excluded and "owned" not in excluded
