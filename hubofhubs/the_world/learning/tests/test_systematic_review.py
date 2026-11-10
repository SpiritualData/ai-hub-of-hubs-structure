"""Learning's review: the record has every part the research standard asks for, exclusions are counted with reasons, grades follow the rule, unknowns are
stated, each candidate has a decision, the applied part and the revisit date are set. Fake search results, no model, no network."""
import csv
from pathlib import Path

import pytest

from hubofhubs.the_world.learning import research_review as rr, review_store
from hubofhubs.the_world.learning.registry_research import RegistryResearch
from hubofhubs.the_world.learning.research_freshness_reader.registry import RegistryScan
from hubofhubs.the_world.learning.systematic_review import SystematicReview
from hubofhubs.the_world.observation import Observation
from hubofhubs.the_world.tools.web_search.search_port import SearchHit, SearchResponse

DAY = "2026-11-10"
WEB = [
    SearchHit("termlib", "https://github.com/acme/termlib", "termlib is a MIT licensed terminal UI library for Python", "2026-09-01"),
    SearchHit("termlib review", "https://blog.example.org/termlib", "An independent review of termlib: stable and widely used", "2026-08-01"),
    SearchHit("termlib", "https://github.com/acme/termlib", "duplicate of the first hit", "2026-09-01"),
    SearchHit("oldkit", "https://github.com/acme/oldkit", "oldkit is archived and deprecated, Apache-2.0", "2025-01-01"),
    SearchHit("gplkit", "https://github.com/acme/gplkit", "gplkit terminal library under the GPL", "2026-07-01"),
    SearchHit("cooking", "https://example.org/pasta", "pasta recipes with no relation", "2026-07-01"),
    SearchHit("nosource", "", "a result with no address", ""),
]
SCIENCE = [{"title": "A study of terminal UIs", "url": "https://papers.example.org/tui", "abstract": "terminal UI study, library comparison", "year": "2026"}]


class Web:
    def search(self, query, *, max_results=5, instruction=None):
        return SearchResponse(hits=list(WEB))


class Science:
    def search(self, queries, *, max_results=None, fresh=False):
        return Observation(kind="query", text="x", hits=list(SCIENCE))

    def fetch(self, url, *, focus=None, fresh=False, full=False, part=None):
        return Observation(kind="error", error="x") if "unreadable" in url or "oldkit" in url else Observation(kind="read", text="This page says MIT license and is maintained.")


def arm(ask=None):
    return SystematicReview(RegistryScan(), Science(), Web(), None, ask=ask)


def run(**changes):
    args = dict(question="which terminal UI libraries are adoptable", decision="adopt or build", weight="quick", intent_id="terminal", today=DAY,
                links=["solution:terminal-experience"], criteria={"exclude_terms": ["recipes"], "since": "2026-01-01", "licence_allow": ["MIT", "Apache-2.0"]})
    args.update(changes)
    return arm().review(**args)


def test_the_record_has_every_part_of_its_size():
    got = run(weight="standard")
    assert got["gaps"] == []
    row = got["research"]
    assert row["size"] == "standard" and row["kind"] == "review" and row["protocol_date"] == DAY == row["done_on"]
    assert len(row["queries"].split(";")) >= 5 and "web search" in row["sources"] and "scholarly search" in row["sources"]
    assert row["refresh_on"] == "2027-02-08" and row["status"] == "open"
    assert all(row[c] for c in rr.SYNTHESIS)


def test_the_smallest_record_is_one_row_with_its_minimum():
    got = run(weight="quick")
    assert got["gaps"] == [] and got["research"]["size"] == "quick" and got["research"]["refresh_on"] == "2026-12-10"
    assert len(got["research"]["queries"].split(";")) <= 3 and "scholarly" not in got["research"]["sources"]


def test_exclusions_are_counted_and_each_has_a_reason():
    got = run()
    reasons = got["screened_out"]
    assert reasons["duplicate of a kept result"] >= 1
    assert sum(reasons.values()) == int(got["research"]["found"]) - int(got["research"]["kept"])
    assert {"no source address", "matched an exclusion term", "older than 2026-01-01"} <= set(reasons)
    assert any(k.startswith("licence GPL") for k in reasons)
    assert got["research"]["screened_out"].count(";") + 1 == len(reasons)


def test_grades_follow_the_rule():
    items = {i["claim"][:12]: i for i in run()["items"]}
    got = run(candidates=["termlib", "oldkit", "gplkit"])
    termlib = [i for i in got["items"] if "termlib" in i["claim"].lower()]
    assert len(termlib) == 2 and {i["grade"] for i in termlib} == {"A"}             # two independent hosts agree
    assert rr.grade([]) == "D" and rr.grade([{"independent": "no"}]) == "D" and rr.grade([{"independent": "yes", "relation": "vendor"}]) == "D"
    assert rr.grade([{"independent": "unknown"}]) == "C" and rr.grade([{"independent": "yes"}]) == "B"
    assert rr.grade([{"independent": "yes"}, {"independent": "yes"}]) == "A" and items


def test_unknowns_are_stated_and_every_candidate_has_a_decision():
    got = run(weight="standard", criteria={"exclude_terms": ["recipes"]}, candidates=["termlib", "oldkit", "gplkit"])
    decisions = {d.split(":")[0]: d.split(":")[1].strip() for d in got["research"]["decisions"].split(";")}
    assert decisions["oldkit"] == "reject" and decisions["gplkit"] == "adopt" and decisions["termlib"] == "adopt"
    assert all(d.count(":") >= 2 for d in got["research"]["decisions"].split(";"))
    assert got["research"]["synthesis_unknown"].startswith(("Not established", "Nothing left"))
    assert run(criteria={"include_terms": ["nothing-matches"]})["research"]["decisions"].startswith("all: no-candidate")


def test_standard_opens_kept_items_and_grades_a_snippet_no_higher_than_c():
    got = run(weight="standard", criteria={"exclude_terms": ["recipes"]}, candidates=["termlib", "oldkit", "gplkit"])
    by = {i["source"]: i for i in got["items"]}
    assert by["https://github.com/acme/termlib"]["verified"] == "cross-checked" and by["https://github.com/acme/termlib"]["grade"] == "A"
    assert by["https://github.com/acme/oldkit"]["verified"] == "snippet" and by["https://github.com/acme/oldkit"]["grade"] == "C"
    assert "read as result snippets only, graded C at most" in got["research"]["limitations"]
    assert rr.cap_grade("A", "snippet", "standard") == "C" and rr.cap_grade("B", "not-opened", "full") == "C" and rr.cap_grade("D", "snippet", "full") == "D"
    assert rr.cap_grade("A", "opened", "standard") == "A" and rr.cap_grade("B", "snippet", "quick") == "B"


def test_quick_opens_nothing_and_stays_cheap():
    opened = []

    class Counting(Science):
        def fetch(self, url, **k):
            opened.append(url)
            return super().fetch(url, **k)
    got = SystematicReview(RegistryScan(), Counting(), Web(), None).review("which terminal UI libraries are adoptable", "adopt or build", weight="quick", today=DAY, intent_id="terminal")
    assert opened == [] and {i["verified"] for i in got["items"]} == {"snippet"}


def test_the_applied_part_says_what_each_item_changed_or_why_not():
    got = run()
    applied = {a["item"]: a["applied"] for a in got["applied"]}
    assert set(applied) == {i["item_id"] for i in got["items"]}
    assert any(v.startswith("knowledge:k-terminal-experience-") for v in applied.values())
    assert all(v.startswith("knowledge:") or v.startswith("not-applied: ") for v in applied.values())
    assert all(i["applied"] for i in got["items"])


def test_the_size_follows_the_weight_of_the_decision():
    assert rr.choose_size({"reversible_days": 0.2}) == "quick" and rr.choose_size({"selects": True}) == "standard"
    assert rr.choose_size({"reaches": 3}) == "standard" and rr.choose_size({"outward": True}) == "full"
    assert rr.choose_size({"dependency": True, "reversible_days": 3}) == "full" and rr.choose_size("standard") == "standard" and rr.choose_size(None) == "quick"


def test_a_candidate_name_never_contains_the_decision_separator():
    from hubofhubs.the_world.learning.systematic_review import candidate_of
    hit = {"title": "PyTermGUI", "url": "https://pypi.org/project/PyTermGUI/7.7.0/", "snippet": ""}
    assert candidate_of(hit, []) == "pypi/PyTermGUI"


def test_a_failing_source_is_a_limitation_not_a_failed_review():
    class Broken(Web):
        def search(self, *a, **k):
            raise RuntimeError("down")
    got = SystematicReview(RegistryScan(), Science(), Broken(), None).review("which libraries", "adopt or build", weight="quick", today=DAY, intent_id="terminal")
    assert "web search failed" in got["research"]["limitations"] and got["research"]["decisions"].startswith("all: defer: no results came back")
    assert got["gaps"] == []


def test_a_model_may_screen_and_write_the_synthesis_and_its_failure_changes_nothing():
    calls = []

    def ask(prompt):
        calls.append(prompt)
        return '{"drop": [{"id": "i1", "reason": "x"}]}' if "drop" in prompt else '{"known": "k.", "contested": "c.", "unknown": "u."}'
    with_model = arm(ask).review("which terminal UI libraries are adoptable", "adopt or build", weight="standard", today=DAY, intent_id="terminal", use_model=True)
    assert len(calls) == 2 and with_model["research"]["synthesis_known"] == "k." and "judged not to bear on the question" in with_model["screened_out"]
    failing = arm(lambda prompt: "not json").review("which terminal UI libraries are adoptable", "adopt or build", weight="standard", today=DAY, intent_id="terminal", use_model=True)
    assert failing["research"]["synthesis_known"].startswith(("Supported", "Nothing"))


def test_the_baseline_returns_a_record_that_lacks_the_standard():
    got = RegistryResearch(RegistryScan(), Science()).review("which terminal UI libraries are adoptable", "adopt", today=DAY, intent_id="terminal")
    assert len(got["gaps"]) >= 8 and any("has no criteria" in g for g in got["gaps"])


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        csv.writer(handle).writerows([header] + rows)


def test_due_lists_reviews_experiments_and_registry_areas_past_their_dates(tmp_path, monkeypatch):
    h = tmp_path / "hubofhubs"
    write(h / "a" / "research.csv", ["research_id", "question", "links", "size", "refresh_on", "status", "done_on"],
          [["r-old", "q?", "solution:s1", "standard", "2026-11-01", "open", "2026-08-01"], ["r-new", "q2?", "area:fresh", "standard", "2027-01-01", "open", "2026-11-01"],
           ["r-done", "q3?", "", "quick", "2026-10-01", "superseded", "2026-09-01"]])
    write(h / "a" / "experiments.csv", ["experiment_id", "research_question", "links", "status", "reevaluate_time"], [["x-1", "focus", "solution:s1", "running", "2026-11-05"]])
    write(h / "registry" / "hubs.csv", ["area", "seat", "last_researched", "candidate_hubs"],
          [["stale_area", "s2", "2026-06-01", "A;B"], ["fresh", "s3", "2026-07-01", ""], ["recent", "s4", "2026-11-01", ""], ["never", "s5", "", ""]])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", h / "registry")
    got = review_store.due(DAY, tmp_path)
    assert [(d["kind"], d["id"]) for d in got] == [("registry-area", "never"), ("registry-area", "stale_area"), ("review", "r-old"), ("experiment", "x-1")]
    assert all(d["request"] and "days_overdue" in d for d in got)
    assert got[1]["days_overdue"] == (__import__("datetime").date(2026, 11, 10) - __import__("datetime").date(2026, 6, 1)).days - 90
    assert review_store.standing_schedule()["cadence"] == "weekly" and review_store.standing_schedule()["name"] == review_store.WEEKLY


def test_an_experiment_with_the_older_field_names_is_still_due(tmp_path, monkeypatch):
    h = tmp_path / "hubofhubs"
    write(h / "a" / "experiments.csv", ["experiment_id", "focus", "links", "status", "reevaluate_on"], [["x-old", "old focus", "", "running", "2026-11-05"]])
    write(h / "registry" / "hubs.csv", ["area", "seat", "last_researched", "candidate_hubs"], [])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", h / "registry")
    got = review_store.due(DAY, tmp_path)
    assert [(d["id"], d["question"], d["due_on"]) for d in got] == [("x-old", "old focus", "2026-11-05")]


def test_a_stored_review_is_found_from_its_finding_and_supersedes_the_earlier_one(tmp_path, monkeypatch):
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", tmp_path / "registry")
    first = run(links=["area:terminal", "solution:terminal-experience"], today="2026-10-01")
    second = run(links=["area:terminal", "solution:terminal-experience"], today=DAY)
    review_store.store(first, tmp_path / "registry")
    review_store.store(second, tmp_path / "registry")
    rows = list(csv.DictReader(open(tmp_path / "registry" / "research.csv")))
    assert [r["status"] for r in rows] == ["superseded", "open"] and len(list(csv.DictReader(open(tmp_path / "registry" / "research_items.csv")))) == 2 * len(second["items"])
    monkeypatch.setattr(review_store, "files", lambda root, name: [tmp_path / "registry" / name])
    assert review_store.finding_review({"area": "terminal", "date_researched": DAY}) == second["research"]["research_id"]
    assert review_store.finding_review({"area": "terminal", "date_researched": "2026-01-01"}) == ""


def test_a_finding_names_its_review_and_old_rows_fall_back_to_area_and_date(tmp_path, monkeypatch):
    folder = tmp_path / "registry"
    write(folder / "hub_findings.csv", ["finding_id", "area", "date_researched", "summary"],
          [["HF-1", "terminal", DAY, "new"], ["HF-2", "terminal", "2026-01-01", "older day"], ["HF-3", "other", DAY, "other area"]])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", folder)
    got = run(links=["area:terminal", "solution:terminal-experience"])
    rid = review_store.store(got, folder)
    rows = {r["finding_id"]: r for r in csv.DictReader(open(folder / "hub_findings.csv"))}
    assert rows["HF-1"]["research_id"] == rid and rows["HF-2"]["research_id"] == "" and rows["HF-3"]["research_id"] == "" and rows["HF-3"]["summary"] == "other area"
    assert list(rows["HF-1"])[-1] == "research_id" and review_store.link_findings(rid, got["research"], folder) == 0
    monkeypatch.setattr(review_store, "files", lambda root, name: [folder / name])
    assert review_store.finding_review(rows["HF-1"]) == rid
    assert review_store.finding_review({"area": "terminal", "date_researched": DAY}) == rid and review_store.finding_review(rows["HF-3"]) == ""
    assert review_store.finding_review({"area": "x", "research_id": "r-own"}) == "r-own"


def test_the_record_agrees_with_the_libraries_own_checker():
    research = pytest.importorskip("esoi.understanding.solution_consideration.research")
    got = run(weight="standard", links=["solution:terminal-experience"])
    row = dict(got["research"], intent_id="terminal")
    assert research.row_problems(row, got["items"]) == []


def test_the_weekly_refresh_is_standing_work_proactivity_reads():
    from hubofhubs.the_intelligence.proactivity.triggers import CalendarAndEvents
    schedule = review_store.standing_schedule(last_run="2026-11-02T09:00:00Z")
    due = CalendarAndEvents().due([schedule], now="2026-11-10T09:00:00Z")
    assert [t["schedule"] for t in due] == [review_store.WEEKLY] and due[0]["request"] == schedule["request"]
    assert CalendarAndEvents().due([review_store.standing_schedule(last_run="2026-11-10T08:00:00Z")], now="2026-11-10T09:00:00Z") == []
