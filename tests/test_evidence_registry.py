"""The public evidence registry is well formed, sourced and public-safe: no model call, no network."""
import csv
import re
from datetime import date
from pathlib import Path

from hubofhubs import registry

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "hubofhubs" / "registry" / "hub_evidence.csv"
COLUMNS = ["evidence_id", "area", "seat", "candidate", "dimension", "measure", "value", "unit", "better", "comparator", "source_url",
           "source_kind", "run_by_independent", "method_disclosed", "n", "benchmark_status", "date_published", "date_checked",
           "confounds", "note"]
REQUIRED = ["evidence_id", "area", "seat", "candidate", "dimension", "measure", "better", "source_url", "source_kind",
            "run_by_independent", "method_disclosed", "benchmark_status", "date_checked", "confounds"]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
MACHINE_PATH = re.compile(r"(/home/|/Users/|/tmp/|C:\\)")
ID_LIKE = re.compile(r"[0-9a-f]{24}|qsk_|sk-ant-|teamdec_")


def rows():
    with open(PATH, newline="") as handle:
        return list(csv.DictReader(handle))


def names_of(area_row, findings):
    return {f["candidate"] for f in registry.findings_of(area_row, findings)} | {n for n, _u, _l in registry.parse_hubs(area_row["candidate_hubs"])} | set(registry.split(area_row["candidate_hubs"]))


def iso(value):
    return date.fromisoformat(value)


def test_columns_are_the_fixed_schema():
    with open(PATH, newline="") as handle:
        assert next(csv.reader(handle)) == COLUMNS
    assert 1 <= len(rows()) <= 60


def test_allowed_values_and_required_fields():
    ids = [r["evidence_id"] for r in rows()]
    assert len(ids) == len(set(ids)), "evidence ids must be unique"
    for r in rows():
        who = r["evidence_id"]
        assert re.fullmatch(r"EV-[a-z0-9-]+", who), who
        for column in REQUIRED:
            assert r[column].strip(), f"{who}: {column} is empty"
        assert r["dimension"] in registry.EVIDENCE_DIMENSIONS, who
        assert r["better"] in registry.EVIDENCE_BETTER, who
        assert r["source_kind"] in registry.EVIDENCE_SOURCE_KINDS, who
        assert r["run_by_independent"] in registry.EVIDENCE_INDEPENDENT, who
        assert r["method_disclosed"] in registry.EVIDENCE_METHOD, who
        assert r["benchmark_status"] in registry.EVIDENCE_STATUS, who
        if r["value"].strip():
            float(r["value"])
            assert r["unit"].strip(), f"{who}: a value needs a unit"
        else:
            assert r["note"].strip(), f"{who}: a row with no value carries the ranking or direction in note"
        if r["n"].strip():
            assert float(r["n"]) > 0, who


def test_candidate_area_and_seat_exist_in_the_registry():
    hubs = registry.read("hubs.csv")
    findings = registry.read("hub_findings.csv")
    by_area = {h["area"]: h for h in hubs}
    for r in rows():
        who = r["evidence_id"]
        assert r["area"] in by_area, f"{who}: unknown area {r['area']}"
        assert by_area[r["area"]]["seat"] == r["seat"], f"{who}: seat does not own the area"
        assert r["candidate"] in names_of(by_area[r["area"]], findings), f"{who}: candidate {r['candidate']!r} not in the area"


def test_every_row_is_sourced_and_dated_and_not_from_the_future():
    today = date.today()
    for r in rows():
        who = r["evidence_id"]
        assert r["source_url"].startswith("https://"), who
        assert iso(r["date_checked"]) <= today, f"{who}: date_checked in the future"
        if r["date_published"].strip():
            assert iso(r["date_published"]) <= today, f"{who}: date_published in the future"
            assert iso(r["date_published"]) <= iso(r["date_checked"]), who


def test_text_is_public_safe_and_has_no_em_dash():
    for r in rows():
        for column, value in r.items():
            assert "\u2014" not in value, (r["evidence_id"], column)
            assert not EMAIL.search(value), (r["evidence_id"], column)
            assert not MACHINE_PATH.search(value), (r["evidence_id"], column)
            assert not ID_LIKE.search(value), (r["evidence_id"], column)
    assert "\u2014" not in PATH.read_text()


def test_evidence_is_comparable_not_a_result_row():
    """A vendor figure never claims to be independent; a comparator-less row says so by leaving it blank, not by guessing."""
    for r in rows():
        if r["source_kind"] in ("vendor_reported", "maintainer_reported"):
            assert r["run_by_independent"] != "yes", r["evidence_id"]
