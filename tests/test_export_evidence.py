"""The library's evidence file is derived from the registry and equals the export: no model call, no network."""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("export_evidence", ROOT / "scripts" / "export_evidence.py")
export = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export)

LIBRARY_HEADER = ["evidence_id", "candidate", "dimension", "measure", "value", "unit", "better", "comparator", "source_url",
                  "source_kind", "run_by_independent", "method_disclosed", "n", "benchmark_status", "date_published", "date_checked",
                  "confounds", "note"]


def read(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def test_derived_file_has_the_library_header_without_area_and_seat():
    with open(export.TARGET, newline="") as handle:
        assert next(csv.reader(handle)) == LIBRARY_HEADER


def test_derived_file_equals_the_export_of_the_registry():
    assert export.TARGET.read_text() == export.export_text()


def test_every_valued_registry_row_survives_with_every_other_column_unchanged():
    source = [r for r in read(export.SOURCE) if r["value"].strip()]
    derived = read(export.TARGET)
    assert len(source) == len(derived)
    for before, after in zip(source, derived):
        kept = {k: v for k, v in before.items() if k not in export.DROPPED}
        kept["candidate"] = export.library_candidate(kept["candidate"])
        assert kept == after
        assert "," not in after["candidate"]


def test_only_rows_with_no_value_are_left_out():
    left_out = {r["evidence_id"] for r in read(export.SOURCE)} - {r["evidence_id"] for r in read(export.TARGET)}
    assert left_out == set(export.omitted_ids())
    assert all(not r["value"].strip() for r in read(export.SOURCE) if r["evidence_id"] in left_out)
