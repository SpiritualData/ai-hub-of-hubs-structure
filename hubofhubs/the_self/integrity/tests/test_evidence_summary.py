"""The evidence table on docs/reference/status.md is generated from the records: every recorded check appears, its figures are the recorded ones, and
a pending or unmeasured thing is shown as such."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
import status  # noqa: E402
from hubofhubs.the_self.integrity import evidence_summary  # noqa: E402

ROOT = status.ROOT


def recorded_components():
    return {row["component"] for row in csv.DictReader(open(ROOT / "esoi" / "results.csv"))}


def test_every_recorded_component_appears_in_the_leaderboard_and_by_arm():
    config, registry = status.records()
    board = evidence_summary.leaderboard_block(config, registry, ROOT)
    by_arm = evidence_summary.arms_block(config, registry)
    for component in recorded_components():
        assert component in by_arm, component
    records = evidence_summary.claims(config, registry, ROOT)
    assert {r["component"] for r in records} == recorded_components()
    rival_rows = [line for line in board.split("### Conformance tests")[0].splitlines()[2:] if line.startswith("| ") and "`)" in line]
    assert len(rival_rows) == len([r for r in records if not r["conformance"]])


def test_the_readme_table_has_one_row_per_seat_and_conformance_checks_are_listed_apart():
    config, registry = status.records()
    block = evidence_summary.evidence_block(config, registry, ROOT)
    rows = [line for line in block.splitlines()[2:] if line.startswith("| ") and "(`" in line]
    assert len(rows) == len({line.split("`")[1] for line in rows})
    assert "Conformance tests (cases written in this repo, no rival, not counted as alternatives)" in block
    assert "(`card-store`) 35/35" in block.split("Conformance tests")[1] and not any("(`card-store`)" in line for line in rows)


def test_every_selected_arm_is_the_leader_on_the_cases_that_chose_it_or_says_why_not():
    config, registry = status.records()
    for record in evidence_summary.claims(config, registry, ROOT):
        if record["deciding"] and not record["apart"] and not record["conformance"] and record["decisions"]:
            assert record["leader"] == record["selected"] or record["pending"] == record["leader"], record["component"]


def test_the_figures_are_the_recorded_ones_not_typed():
    config, registry = status.records()
    block = evidence_summary.leaderboard_block(config, registry, ROOT)
    rows = [r for r in csv.DictReader(open(ROOT / "esoi" / "results.csv")) if r["component"] == "card_store" and not r["sample"]]
    last = rows[-1]
    assert f"{last['passed']}/{last['cases']}" in block


def test_a_lead_is_labelled_significant_or_not_and_a_floor_is_shown_as_pending():
    config, registry = status.records()
    block = evidence_summary.leaderboard_block(config, registry, ROOT)
    assert "two-sided McNemar p=" in block and "one-sided" not in block
    assert "not significant (two-sided McNemar p=" in block      # a p above 0.05 is never called a win
    assert "p=," not in block and "{n}" not in block and "private corpus" not in block


def test_unmeasured_seats_and_arms_are_listed_with_a_reason():
    config, registry = status.records()
    text = evidence_summary.unmeasured_block(config, registry, ROOT)
    for seat in ("critical-thinking", "system-integrity"):
        assert f"`{seat}`" in text
    assert all(len(line) > 40 for line in text.splitlines())


def test_the_labels_name_only_real_pages_and_anchors():
    page = (ROOT / "docs" / "explanation" / "what-public-research-says.md").read_text().lower()
    for row in csv.DictReader(open(ROOT / "docs" / "reference" / "evidence-labels.csv")):
        if row["anchor"]:
            heading = row["anchor"].replace("-", " ").split()[0]
            assert heading in page, row["key"]


def test_the_headline_counts_real_alternatives_only():
    config, registry = status.records()
    areas = evidence_summary.counted_arms(config, ROOT)
    every = [arm for arms in areas.values() for arm in arms]
    assert "zero_config" not in every                    # the single-scenario assembly is mechanics, not an alternative
    assert {"none", "single_provider"} <= set(every)     # diagnostic bounds are ranked alternatives and counted
    headline = evidence_summary.headline_block(config, registry, ROOT)
    assert headline.startswith(f"**{len(every)} alternatives measured across {len(areas)} areas, from ")
    assert evidence_summary.compact_headline(config, ROOT).startswith(f"{len(every)} alternatives measured")


def test_the_leaderboard_links_resolve_from_its_own_folder():
    config, registry = status.records()
    board = evidence_summary.leaderboard_block(config, registry, ROOT)
    assert "](docs/" not in board and "](../explanation/" in board
