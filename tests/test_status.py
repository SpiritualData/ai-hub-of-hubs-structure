import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import status  # noqa: E402


def test_readme_table_lists_every_seat_with_its_area_count():
    from hubofhubs import registry
    block = status.build()
    hubs = registry.read("hubs.csv")
    assert len(status.seats()) == 12, "the twelve seats of the mind"
    for seat, part in status.seats():
        count = sum(1 for r in hubs if r["seat"] == seat)
        assert f"| {seat} | {part} | {count} |" in block
    assert {r["seat"] for r in hubs} <= {s for s, _ in status.seats()}, "every area serves a known seat"
    assert f"{len(hubs)} areas" in block


def test_the_detail_file_lists_every_area():
    from hubofhubs import registry
    detail = status.build_detail()
    for row in registry.read("hubs.csv"):
        assert f"| {row['area']} |" in detail


def test_rewrite_is_idempotent_and_never_grows():
    text = f"top\n{status.render_docs.STATUS_BEGIN}\nstale one\nstale two\n{status.render_docs.STATUS_END}\nbottom\n"
    once = status.rewrite(text, status.build())
    twice = status.rewrite(once, status.build())
    assert once == twice
    assert once.startswith("top\n") and once.endswith("bottom\n")
    assert "stale" not in once


def test_generated_files_are_current():
    assert status.main(["--check"]) == 0


# The README shows one row per seat, so its size does not grow with the registry (the earlier one-row-per-area table broke the
# cap once research was broken into sub-solution areas). The area detail lives in docs/registry.md, which is generated, not capped.
def test_readme_stays_small():
    readme = (status.ROOT / "README.md").read_text()
    assert status.rewrite(readme, status.build()) == readme
    assert len(readme.splitlines()) <= 120


def test_the_detail_file_shows_each_areas_call():
    from hubofhubs import registry
    detail = status.build_detail()
    assert "| Call |" in detail
    for row in registry.read("hubs.csv"):
        assert f"| {row['status']} | {row['call'] or '-'} |" in detail, row["area"]
