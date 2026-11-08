"""The public priors of Delegated Agent Sessions follow the prior rule of docs/explanation/public-evidence.md: no model call, no network."""
import csv
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
PRIORS = HERE / "public_priors.csv"
EVIDENCE = ROOT / "hubofhubs" / "registry" / "hub_evidence.csv"
COLUMNS = ["arm_id", "harness", "provider", "tier", "prior", "grade", "basis_evidence_ids", "measure_first", "reason",
           "date_checked", "expires"]
MAX_AGE_DAYS = 90          # a prior expires 90 days after the boards were read
MAX_ROW_AGE_DAYS = 180     # a basis row run longer ago than this does not count


def read(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def evidence():
    return {row["evidence_id"]: row for row in read(EVIDENCE)}


def test_columns_and_arm_names():
    with open(PRIORS, newline="") as handle:
        assert next(csv.reader(handle)) == COLUMNS
    rows = read(PRIORS)
    assert len({r["arm_id"] for r in rows}) == len(rows)
    for r in rows:
        assert r["arm_id"] == f"{r['harness']}@provider={r['provider']},tier={r['tier']}", r["arm_id"]
        assert r["measure_first"] in ("yes", "no"), r["arm_id"]
        assert r["reason"].strip() and "—" not in r["reason"], r["arm_id"]


def test_a_prior_is_a_graded_published_number_or_empty():
    known = evidence()
    for r in read(PRIORS):
        ids = [i for i in r["basis_evidence_ids"].split(";") if i]
        assert all(i in known for i in ids), (r["arm_id"], [i for i in ids if i not in known])
        if not r["prior"]:
            assert not r["grade"], f"{r['arm_id']}: a grade with no prior"
            continue
        assert 0.0 <= float(r["prior"]) <= 1.0, r["arm_id"]
        assert r["grade"] in ("A", "B", "C"), f"{r['arm_id']}: a prior needs grade C or better"
        counting = [known[i] for i in ids if known[i]["dimension"] == "quality" and known[i]["benchmark_status"] == "live"]
        values = {round(float(row["value"]) / 100, 4) for row in counting if row["unit"] == "percent"}
        assert round(float(r["prior"]), 4) in values, f"{r['arm_id']}: the prior must be a published live-benchmark value"
        if r["reason"].startswith("Borrowed"):
            assert r["grade"] in ("B", "C"), f"{r['arm_id']}: a borrowed prior is one letter below its rows, so never A"


def test_expiry_and_row_age():
    known = evidence()
    for r in read(PRIORS):
        checked, expires = date.fromisoformat(r["date_checked"]), date.fromisoformat(r["expires"])
        assert checked <= date.today(), r["arm_id"]
        assert expires <= checked + timedelta(days=MAX_AGE_DAYS), r["arm_id"]
        if r["prior"]:
            for i in filter(None, r["basis_evidence_ids"].split(";")):
                published = known[i]["date_published"]
                if published and known[i]["benchmark_status"] == "live":
                    assert checked - date.fromisoformat(published) <= timedelta(days=MAX_ROW_AGE_DAYS), (r["arm_id"], i)
                    assert expires <= date.fromisoformat(published) + timedelta(days=MAX_ROW_AGE_DAYS), (r["arm_id"], i)
