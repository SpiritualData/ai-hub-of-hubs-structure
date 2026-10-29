import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import status  # noqa: E402


def test_build_lists_every_seat_and_marks_empty_ones():
    block = status.build()
    for row in status.read("solutions"):
        assert f"| {row['solution_id']} |" in block
    assert "no arm yet" in block


def test_rewrite_is_idempotent_and_never_grows():
    text = f"top\n{status.START}\nstale one\nstale two\n{status.END}\nbottom\n"
    once = status.rewrite(text, status.build())
    twice = status.rewrite(once, status.build())
    assert once == twice
    assert once.startswith("top\n") and once.endswith("bottom\n")
    assert "stale" not in once


def test_readme_status_is_current():
    readme = (status.ROOT / "README.md").read_text()
    assert status.rewrite(readme, status.build()) == readme
