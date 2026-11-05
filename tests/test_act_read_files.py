"""File Reading: lists and reads the text files of a folder, never outside it."""
import pytest

from hubofhubs.act.read_files import FolderReader


def test_lists_and_reads_text_files_and_skips_what_is_not_text(tmp_path):
    (tmp_path / "a.py").write_text("print('a')\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("# b\n")
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x80")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    reader = FolderReader()
    assert reader.list(str(tmp_path)) == ["a.py", "blob.bin", "sub/b.md"]
    assert reader.list(str(tmp_path), (".md",)) == ["sub/b.md"]
    assert reader.read(str(tmp_path)) == {"a.py": "print('a')\n", "sub/b.md": "# b\n"}


def test_a_path_outside_the_folder_is_refused(tmp_path):
    (tmp_path / "inner").mkdir()
    (tmp_path / "secret.txt").write_text("s")
    with pytest.raises(ValueError, match="outside the folder"):
        FolderReader().read(str(tmp_path / "inner"), ["../secret.txt"])
