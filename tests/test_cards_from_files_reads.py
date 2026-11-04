"""The bootstrap read meter of cards_from_files: opens, distinct files and bytes under the corpus root only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation"))

from cards_from_files.reads import Reads


def test_reads_count_opens_files_and_bytes_under_the_root_and_nothing_else(tmp_path):
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / "a.py").write_text("abcd")
    (tmp_path / "root" / "b.py").write_text("xy")
    (tmp_path / "other.txt").write_text("not counted")
    with Reads(tmp_path / "root") as reads:
        (tmp_path / "root" / "a.py").read_text()
        (tmp_path / "root" / "a.py").read_text()
        (tmp_path / "root" / "b.py").read_bytes()
        (tmp_path / "other.txt").read_text()
        (tmp_path / "root" / "c.py").write_text("written, not read")
    assert (reads.opens, reads.files, reads.bytes) == (3, 2, 4 + 4 + 2)
