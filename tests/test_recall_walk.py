"""Directory pruning for the file-indexing walks: the baseline, .gitignore names, the consumer's extras, mounted subtrees."""
import os

from hubofhubs.recall.walk import effective_skip_dirs, is_claude_state_file, parse_gitignore_names, prune_dirnames, skip_subtrees


def test_gitignore_names_keep_only_bare_directory_names(tmp_path):
    (tmp_path / ".gitignore").write_text("# c\nbuild/\n/out\n*.log\n!keep\nsrc/gen\njdk\n")
    assert parse_gitignore_names(tmp_path) == {"build", "out", "jdk"}
    assert parse_gitignore_names(tmp_path / "missing") == set()


def test_the_skip_set_is_the_baseline_plus_gitignore_plus_the_consumers_extras(tmp_path):
    (tmp_path / ".gitignore").write_text("scratch\n")
    skip = effective_skip_dirs(tmp_path, extra=["backups", " ", "archive"])
    assert {"node_modules", "__pycache__", "scratch", "backups", "archive"} <= skip and "" not in skip


def test_the_hub_reads_no_environment_for_the_skip_set(tmp_path, monkeypatch):
    monkeypatch.setenv("QAR_SKIP_DIRS", "from_the_environment")
    assert "from_the_environment" not in effective_skip_dirs(tmp_path)


def test_prune_drops_skipped_nested_gitignored_and_hidden_directories(tmp_path):
    (tmp_path / ".gitignore").write_text("nested_ignored\n")
    names = ["src", "node_modules", "nested_ignored", ".hidden", "docs"]
    prune_dirnames(names, current=tmp_path, base_skip=effective_skip_dirs(tmp_path))
    assert names == ["src", "docs"]


def test_a_mounted_subtree_is_skipped_for_the_duration_of_the_block(tmp_path):
    names = ["mount", "other"]
    with skip_subtrees([tmp_path / "mount"]):
        prune_dirnames(names, current=tmp_path, base_skip=set())
    assert names == ["other"]
    again = ["mount", "other"]
    prune_dirnames(again, current=tmp_path, base_skip=set())
    assert again == ["mount", "other"]


def test_claude_code_state_files_are_recognised_by_prefix():
    assert is_claude_state_file(".claude.json") and is_claude_state_file(".claude.json.backup.123")
    assert not is_claude_state_file("claude.json") and not is_claude_state_file("notes.md")
