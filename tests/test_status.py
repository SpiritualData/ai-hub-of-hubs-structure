import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import status  # noqa: E402


def test_table_lists_every_area():
    from hubofhubs import registry
    block = status.build()
    for row in registry.read("hubs.csv"):
        assert f"| {row['area']} |" in block


def test_rewrite_is_idempotent_and_never_grows():
    text = f"top\n{status.render_docs.STATUS_BEGIN}\nstale one\nstale two\n{status.render_docs.STATUS_END}\nbottom\n"
    once = status.rewrite(text, status.build())
    twice = status.rewrite(once, status.build())
    assert once == twice
    assert once.startswith("top\n") and once.endswith("bottom\n")
    assert "stale" not in once


def test_readme_table_is_current():
    readme = (status.ROOT / "README.md").read_text()
    assert status.rewrite(readme, status.build()) == readme
    assert len(readme.splitlines()) <= 120
