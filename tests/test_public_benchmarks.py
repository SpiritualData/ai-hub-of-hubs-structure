"""The public benchmark and reporting-format registries are well formed, honest and public-safe: no model call, no network."""
import csv
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "hubofhubs" / "registry"

BENCH_COLUMNS = ["benchmark_id", "name", "url", "area", "seat", "what_it_measures", "run_by", "independent", "license", "status",
                 "use", "usable_as_metric_input", "evaluated_arms_or_models", "covers_our_circumstance", "cost_to_run",
                 "caveats", "our_offline_set", "source_url", "date_checked", "source_quality"]
FORMAT_COLUMNS = ["format", "url", "what_it_records", "license", "fit_for_esoi", "smallest_bridge", "date_checked", "source_quality"]
USES = {"metric-input", "run-subset", "run-full", "prior-only", "not-useful"}
INDEPENDENT = {"yes", "no", "vendor"}
COVERS = {"yes", "partly", "no"}
USABLE_PREFIXES = ("yes:", "prior-only:", "no:")
SEATS_THAT_MUST_APPEAR = ["hold-the-intents", "take-in-the-world", "remember-and-recall", "reason-and-answer", "know-the-world",
                          "think-critically", "act-in-the-world", "watch-for-risk", "assemble-the-whole", "stay-current",
                          "keep-it-generic", "connect-any-integration"]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
MACHINE_PATH = re.compile(r"(/home/|/Users/|/tmp/|C:\\)")
ID_LIKE = re.compile(r"[0-9a-f]{24}|qsk_|sk-ant-|teamdec_")      # a database id, an API key or a decision id


def read(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def solution_ids():
    return {row["solution_id"] for row in read(ROOT / "esoi" / "solutions.csv")}


def is_link(value):
    return value.startswith(("http://", "https://")) or (value.startswith("docs/") and value.split("#")[0].endswith(".md"))


def test_benchmark_columns_and_rows_exist():
    path = REGISTRY / "public_benchmarks.csv"
    with open(path, newline="") as handle:
        assert next(csv.reader(handle)) == BENCH_COLUMNS
    assert len(read(path)) >= 40


def test_every_benchmark_row_is_complete_and_valid():
    rows = read(REGISTRY / "public_benchmarks.csv")
    ids = [row["benchmark_id"] for row in rows]
    assert len(ids) == len(set(ids)), "benchmark ids must be unique"
    for row in rows:
        who = row["benchmark_id"]
        for column in BENCH_COLUMNS:
            if column == "our_offline_set":
                continue
            assert row[column].strip(), f"{who}: {column} is empty"
        assert re.fullmatch(r"[a-z0-9_]+", who), who
        assert row["use"] in USES, f"{who}: use {row['use']!r}"
        assert row["independent"] in INDEPENDENT, who
        assert row["covers_our_circumstance"] in COVERS, who
        assert row["usable_as_metric_input"].startswith(USABLE_PREFIXES), f"{who}: usable_as_metric_input needs a verdict and a reason"
        assert row["url"].startswith(("http://", "https://")) and row["source_url"].startswith(("http://", "https://")), who
        assert date.fromisoformat(row["date_checked"]) <= date.today(), who
        assert row["our_offline_set"] == "" or re.fullmatch(r"[a-z0-9_]+", row["our_offline_set"]), who


def test_the_use_and_the_reason_agree():
    for row in read(REGISTRY / "public_benchmarks.csv"):
        who, verdict = row["benchmark_id"], row["usable_as_metric_input"].split(":")[0]
        if row["use"] == "metric-input":
            assert verdict == "yes", who
        if row["use"] == "not-useful":
            assert verdict == "no", f"{who}: a not-useful row cannot feed a metric"
        if row["use"] == "prior-only":
            assert verdict in ("prior-only", "no"), who
        if row["use"] in ("run-subset", "run-full"):
            assert row["cost_to_run"].strip() and row["cost_to_run"] != "n/a", who


def test_a_vendor_or_unclear_source_never_decides_alone():
    for row in read(REGISTRY / "public_benchmarks.csv"):
        if row["independent"] in ("vendor", "no") and row["use"] == "metric-input":
            assert "triangulat" in row["usable_as_metric_input"], f"{row['benchmark_id']}: single non-independent source must be triangulated"
        if row["independent"] == "vendor":
            assert row["use"] in ("prior-only", "not-useful"), f"{row['benchmark_id']}: vendor-run results are priors"


def test_unread_sources_are_marked_unverified():
    for row in read(REGISTRY / "public_benchmarks.csv"):
        quality = row["source_quality"]
        assert quality.startswith(("official", "secondary", "unverified")), row["benchmark_id"]
        if quality.startswith("unverified"):
            assert row["use"] in ("prior-only", "not-useful", "run-subset"), row["benchmark_id"]


def test_seats_exist_and_every_seat_is_covered():
    known = solution_ids()
    seats = {row["seat"] for row in read(REGISTRY / "public_benchmarks.csv")}
    assert seats <= known, f"unknown seats: {sorted(seats - known)}"
    assert not set(SEATS_THAT_MUST_APPEAR) - seats, f"seats without a row: {sorted(set(SEATS_THAT_MUST_APPEAR) - seats)}"


def test_reporting_formats_are_complete():
    path = REGISTRY / "reporting_formats.csv"
    with open(path, newline="") as handle:
        assert next(csv.reader(handle)) == FORMAT_COLUMNS
    rows = read(path)
    names = [row["format"] for row in rows]
    assert len(names) == len(set(names))
    for row in rows:
        for column in FORMAT_COLUMNS:
            assert row[column].strip(), f"{row['format']}: {column} is empty"
        assert is_link(row["url"]), row["format"]
        assert date.fromisoformat(row["date_checked"]) <= date.today()
        assert row["source_quality"].startswith(("official", "secondary", "unverified", "read in the esoi")), row["format"]
    assert {"esoi results.csv", "Hugging Face .eval_results YAML", "Inspect AI EvalLog (.eval and .json)"} <= set(names)


def test_the_files_are_public_safe():
    for path in (REGISTRY / "public_benchmarks.csv", REGISTRY / "reporting_formats.csv", ROOT / "docs" / "public-benchmarks.md"):
        text = path.read_text()
        assert "\u2014" not in text and "\u2013" not in text, f"{path.name}: dash characters are not allowed"
        assert not EMAIL.search(text), f"{path.name}: contains an email address"
        assert not MACHINE_PATH.search(text), f"{path.name}: contains a machine path"
        assert not ID_LIKE.search(text), f"{path.name}: contains an id or a key"


def test_the_doc_is_short_and_states_the_rule():
    text = (ROOT / "docs" / "public-benchmarks.md").read_text()
    assert len(text.splitlines()) < 120
    for phrase in ("Null when not covered", "Triangulate", "Sanity gate", "Record version and date", "source type"):
        assert phrase.lower() in text.lower(), phrase
