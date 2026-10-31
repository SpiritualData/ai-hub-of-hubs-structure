"""The README evidence table is generated from the records: every recorded check appears, its figures are the recorded ones, and
a pending or unmeasured thing is shown as such."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import status  # noqa: E402
from hubofhubs import evidence_summary  # noqa: E402

ROOT = status.ROOT


def recorded_components():
    return {row["component"] for row in csv.DictReader(open(ROOT / "esoi" / "results.csv"))}


def test_every_recorded_component_appears_in_the_evidence_table_and_by_arm():
    config, registry = status.records()
    block = evidence_summary.evidence_block(config, registry, ROOT)
    by_arm = evidence_summary.arms_block(config, registry)
    for component in recorded_components():
        assert component in by_arm, component
    assert len([line for line in block.splitlines() if line.startswith("| `")]) == len(recorded_components())


def test_the_figures_are_the_recorded_ones_not_typed():
    config, registry = status.records()
    block = evidence_summary.evidence_block(config, registry, ROOT)
    rows = [r for r in csv.DictReader(open(ROOT / "esoi" / "results.csv")) if r["component"] == "card_store" and not r["sample"]]
    last = rows[-1]
    assert f"{last['passed']}/{last['cases']}" in block


def test_a_lead_is_labelled_significant_or_not_and_a_floor_is_shown_as_pending():
    config, registry = status.records()
    block = evidence_summary.evidence_block(config, registry, ROOT)
    assert "McNemar p=" in block
    assert "not separated from" in block


def test_unmeasured_seats_and_arms_are_listed_with_a_reason():
    config, registry = status.records()
    text = evidence_summary.unmeasured_block(config, registry, ROOT)
    for seat in ("hold-the-intents", "think-critically", "keep-it-generic"):
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
    for floor in ("none", "single_provider", "zero_config"):
        assert floor not in every
    headline = evidence_summary.headline_block(config, registry, ROOT)
    assert headline.startswith(f"**{len(every)} alternatives measured across {len(areas)} areas, from ")
    assert evidence_summary.compact_headline(config, ROOT).startswith(f"{len(every)} alternatives measured")
