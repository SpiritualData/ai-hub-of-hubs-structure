import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import status  # noqa: E402


def test_readme_table_lists_every_seat_with_its_area_count():
    from hubofhubs.the_world.learning.research_freshness_reader import registry
    block = status.build()
    hubs = registry.read("hubs.csv")
    from hubofhubs.the_self.integrity import evidence_summary
    assert len(status.seats()) == len(evidence_summary.MIND_TREE), "every part of the tree is a solution of the records"
    assert len([1 for _sid, inside in evidence_summary.MIND_TREE if not inside]) == 5, "five containers at the top"
    for seat, part, inside in status.seats():
        count = sum(1 for r in hubs if r["seat"] == seat)
        assert f"| {part} | {inside or 'the hub'} | {count} |" in block
    assert {r["seat"] for r in hubs} <= {s for s, _, _ in status.seats()}, "every area serves a known seat"
    assert f"{len(hubs)} areas" in block


def test_every_solution_of_the_records_has_one_place_in_the_tree():
    from esoi.intents import read_tree
    from hubofhubs.the_self.integrity import evidence_summary
    placed = [sid for sid, _inside in evidence_summary.MIND_TREE]
    recorded = {r["solution_id"] for r in read_tree(status.ROOT / "esoi", "solutions.csv")}
    assert len(placed) == len(set(placed)) and set(placed) == recorded
    assert all(inside in placed for _sid, inside in evidence_summary.MIND_TREE if inside)


def test_the_containers_table_names_each_container_with_its_parts():
    block = status.build_containers()
    for name, sid, evolves, parts in status.containers():
        assert f"| {name} | {evolves} |" in block and f"`{sid}`" in block and parts


def test_the_detail_file_lists_every_area():
    from hubofhubs.the_world.learning.research_freshness_reader import registry
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


# The README shows one row per seat, so its size does not grow with the registry (cap: 200 lines, which holds the plain-language list of every solution) (the earlier one-row-per-area table broke the
# cap once research was broken into sub-solution areas). The area detail lives in docs/reference/registry.md, which is generated, not capped.
def test_readme_stays_small():
    readme = (status.ROOT / "README.md").read_text()
    assert len(readme.splitlines()) <= 200
    page = (status.ROOT / "docs" / "explanation" / "the-mind-map.md").read_text()   # the seats table lives on the mind map page
    assert status.rewrite(page, status.build()) == page


def test_the_detail_file_shows_each_areas_call():
    from hubofhubs.the_world.learning.research_freshness_reader import registry
    detail = status.build_detail()
    assert "| Call |" in detail
    for row in registry.read("hubs.csv"):
        assert f"| {row['status']} | {row['call'] or '-'} |" in detail, row["area"]
