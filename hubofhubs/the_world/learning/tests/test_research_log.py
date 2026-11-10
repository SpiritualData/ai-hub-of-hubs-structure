"""research_log links research to a solution by each route, dates it, and finds what is due: fixture CSVs, no model, no network."""
import csv
from pathlib import Path

from hubofhubs.the_world.learning.research_log import due_solutions, research_log, render


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(header)
        w.writerows(rows)


def repo(tmp_path):
    h = tmp_path / "hubofhubs"
    write(h / "a" / "solutions.csv", ["solution_id"], [["sol-a"]])
    write(h / "b" / "solutions.csv", ["solution_id"], [["sol-b"], ["sol-c"]])
    write(h / "a" / "knowledge.csv", ["knowledge_id", "claim", "solution_ids", "recorded", "expiration"],
          [["k1", "claim one", "sol-a;sol-b", "2026-10-01", "2026-12-01"], ["k2", "other", "sol-b", "2026-10-02", ""]])
    write(h / "a" / "public_priors.csv", ["arm_id", "grade", "prior", "reason", "basis_evidence_ids", "date_checked", "expires"],
          [["arm1", "B", "0.5", "because", "EV-1", "2026-09-01", "2026-11-30"]])
    ev = ["evidence_id", "seat", "candidate", "dimension", "measure", "value", "unit", "date_checked", "date_published"]
    write(h / "registry" / "hub_evidence.csv", ev, [["EV-2", "sol-a", "cand", "speed", "m", "1", "s", "2026-10-20", ""]])
    write(tmp_path / "esoi" / "evidence.csv", ev, [["EV-1", "", "cand", "quality", "m", "2", "pct", "", "2026-08-15"], ["EV-9", "", "x", "y", "m", "3", "", "2026-10-30", ""]])
    write(h / "registry" / "hubs.csv", ["area", "seat", "recommendation", "last_researched"], [["area1", "sol-a", "KEEP it", "2026-10-30"]])
    return tmp_path


def test_each_route_links_and_unlinked_evidence_is_left_out(tmp_path):
    log = research_log("sol-a", repo(tmp_path), "2026-11-09")
    by_kind = {e["kind"]: e for e in log["entries"]}
    assert set(by_kind) == {"knowledge", "prior", "evidence", "registry"}
    ids = " ".join(e["source"] for e in log["entries"])
    assert "EV-1" in ids and "EV-2" in ids and "EV-9" not in ids and "k2" not in ids
    assert by_kind["prior"]["source"] == "hubofhubs/a/public_priors.csv arm1"
    assert research_log("sol-b", repo(tmp_path), "2026-11-09")["entries"][0]["source"].endswith("k2")


def test_priors_do_not_leak_to_other_solution_in_other_folder(tmp_path):
    log = research_log("sol-c", repo(tmp_path), "2026-11-09")
    assert log["never"] and log["last"] == "" and log["next_due"] == "" and log["entries"] == []


def test_ordering_and_default_expiry(tmp_path):
    log = research_log("sol-a", repo(tmp_path), "2026-11-09")
    dates = [e["date"] for e in log["entries"]]
    assert dates == sorted(dates, reverse=True) and log["last"] == "2026-10-30"
    ev1 = [e for e in log["entries"] if e["source"].endswith("EV-1")][0]
    assert ev1["expires"] == "" and ev1["date"] == "2026-08-15"   # date_published when there is no date_checked
    assert log["next_due"] == "2026-11-13" and not log["overdue"]   # 2026-08-15 plus 90 days


def test_overdue_by_own_expiry_and_by_default(tmp_path):
    root = repo(tmp_path)
    late = research_log("sol-a", root, "2026-12-01")
    assert {e["kind"] for e in late["overdue"]} == {"prior", "evidence"}   # prior 11-30, EV-1 11-13; knowledge expires on the day itself, EV-2 01-18
    assert [e["source"] for e in late["overdue"] if e["kind"] == "evidence"] == ["esoi/evidence.csv EV-1"]
    assert not [e for e in late["entries"] if e["kind"] == "registry"][0]["due"]


def test_due_lists_overdue_then_never(tmp_path):
    due = due_solutions(repo(tmp_path), "2026-12-01")
    assert [g["solution"] for g in due] == ["sol-a", "sol-b", "sol-c"] or [g["solution"] for g in due][-1] == "sol-c"
    assert due[-1]["never"] and not due[0]["never"]


def test_render_lines(tmp_path):
    root = repo(tmp_path)
    assert render(research_log("sol-a", root, "2026-11-09")).splitlines()[-1] == "last researched 2026-10-30; next due 2026-11-13"
    assert render(research_log("sol-c", root, "2026-11-09")) == "never researched"
