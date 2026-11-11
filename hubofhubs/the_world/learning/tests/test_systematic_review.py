"""Learning's review (an investigation of kind review): the record has every part the knowledge search standard asks for, exclusions are counted with reasons, grades follow the rule, unknowns are
stated, each candidate has a decision, the applied part and the revisit date are set. Fake search results, no model, no network."""
from types import SimpleNamespace
import csv
from pathlib import Path

import pytest

from hubofhubs.the_world.learning import investigation_record as inv, investigation_store
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
    row = got["investigation"]
    assert row["size"] == "standard" and row["kind"] == "review" and row["protocol_date"] == DAY == row["done_on"]
    assert len(row["queries"].split(";")) >= 5 and "web search" in row["sources"] and "scholarly search" in row["sources"]
    assert row["refresh_on"] == "2027-02-08" and row["status"] == "open"
    assert all(row[c] for c in inv.SYNTHESIS)


def test_the_smallest_record_is_one_row_with_its_minimum():
    got = run(weight="quick")
    assert got["gaps"] == [] and got["investigation"]["size"] == "quick" and got["investigation"]["refresh_on"] == "2026-12-10"
    assert len(got["investigation"]["queries"].split(";")) <= 3 and "scholarly" not in got["investigation"]["sources"]


def test_exclusions_are_counted_and_each_has_a_reason():
    got = run()
    reasons = got["screened_out"]
    assert reasons["duplicate of a kept result"] >= 1
    assert sum(reasons.values()) == int(got["investigation"]["found"]) - int(got["investigation"]["kept"])
    assert {"no source address", "matched an exclusion term", "older than 2026-01-01"} <= set(reasons)
    assert any(k.startswith("licence GPL") for k in reasons)
    assert got["investigation"]["screened_out"].count(";") + 1 == len(reasons)


def test_grades_follow_the_rule():
    items = {i["claim"][:12]: i for i in run()["items"]}
    got = run(candidates=["termlib", "oldkit", "gplkit"])
    termlib = [i for i in got["items"] if "termlib" in i["claim"].lower()]
    assert len(termlib) == 2 and {i["grade"] for i in termlib} == {"A"}             # two independent hosts agree
    assert inv.grade([]) == "D" and inv.grade([{"independent": "no"}]) == "D" and inv.grade([{"independent": "yes", "relation": "vendor"}]) == "D"
    assert inv.grade([{"independent": "unknown"}]) == "C" and inv.grade([{"independent": "yes"}]) == "B"
    assert inv.grade([{"independent": "yes"}, {"independent": "yes"}]) == "A" and items


def test_unknowns_are_stated_and_every_candidate_has_a_decision():
    got = run(weight="standard", criteria={"exclude_terms": ["recipes"]}, candidates=["termlib", "oldkit", "gplkit"])
    decisions = {d.split(":")[0]: d.split(":")[1].strip() for d in got["investigation"]["decisions"].split(";")}
    assert decisions["oldkit"] == "reject" and decisions["gplkit"] == "adopt" and decisions["termlib"] == "adopt"
    assert all(d.count(":") >= 2 for d in got["investigation"]["decisions"].split(";"))
    assert got["investigation"]["synthesis_unknown"].startswith(("Not established", "Nothing left"))
    assert run(criteria={"include_terms": ["nothing-matches"]})["investigation"]["decisions"].startswith("all: no-candidate")


def test_standard_opens_kept_items_and_grades_a_snippet_no_higher_than_c():
    got = run(weight="standard", criteria={"exclude_terms": ["recipes"]}, candidates=["termlib", "oldkit", "gplkit"])
    by = {i["source"]: i for i in got["items"]}
    assert by["https://github.com/acme/termlib"]["verified"] == "cross-checked" and by["https://github.com/acme/termlib"]["grade"] == "A"
    assert by["https://github.com/acme/oldkit"]["verified"] == "snippet" and by["https://github.com/acme/oldkit"]["grade"] == "C"
    assert "read as result snippets only, graded C at most" in got["investigation"]["limitations"]
    assert inv.cap_grade("A", "snippet", "standard") == "C" and inv.cap_grade("B", "not-opened", "full") == "C" and inv.cap_grade("D", "snippet", "full") == "D"
    assert inv.cap_grade("A", "opened", "standard") == "A" and inv.cap_grade("B", "snippet", "quick") == "B"


def test_quick_opens_its_top_three_pages_and_an_unreadable_page_stays_a_snippet():
    opened = []

    class Counting(Science):
        def fetch(self, url, **k):
            opened.append(url)
            return super().fetch(url, **k)
    got = SystematicReview(RegistryScan(), Counting(), Web(), None).review("which terminal UI libraries are adoptable", "adopt or build", weight="quick", today=DAY, intent_id="terminal")
    assert len(opened) == 3 and len(set(opened)) == 3
    verified = [i["verified"] for i in got["items"]]
    assert verified.count("snippet") == len(verified) - len([v for v in verified if v != "snippet"]) and any(v != "snippet" for v in verified)

    class Unreadable(Science):
        def fetch(self, url, **k):
            return SimpleNamespace(kind="error", text="")
    again = SystematicReview(RegistryScan(), Unreadable(), Web(), None).review("which terminal UI libraries are adoptable", "adopt or build", weight="quick", today=DAY, intent_id="terminal")
    assert {i["verified"] for i in again["items"]} == {"snippet"} and "a page could not be opened" in again["investigation"]["limitations"]


def test_the_applied_part_says_what_each_item_changed_or_why_not():
    got = run()
    applied = {a["item"]: a["applied"] for a in got["applied"]}
    assert set(applied) == {i["item_id"] for i in got["items"]}
    assert any(v.startswith("knowledge:k-terminal-experience-") for v in applied.values())
    assert all(v.startswith("knowledge:") or v.startswith("not-applied: ") for v in applied.values())
    assert all(i["applied"] for i in got["items"])


def test_the_size_follows_the_weight_of_the_decision():
    assert inv.choose_size({"reversible_days": 0.2}) == "quick" and inv.choose_size({"selects": True}) == "standard"
    assert inv.choose_size({"reaches": 3}) == "standard" and inv.choose_size({"outward": True}) == "full"
    assert inv.choose_size({"dependency": True, "reversible_days": 3}) == "full" and inv.choose_size("standard") == "standard" and inv.choose_size(None) == "quick"


def test_a_candidate_name_never_contains_the_decision_separator():
    from hubofhubs.the_world.learning.systematic_review import candidate_of
    hit = {"title": "PyTermGUI", "url": "https://pypi.org/project/PyTermGUI/7.7.0/", "snippet": ""}
    assert candidate_of(hit, []) == "pypi/PyTermGUI"


def test_a_failing_source_is_a_limitation_not_a_failed_review():
    class Broken(Web):
        def search(self, *a, **k):
            raise RuntimeError("down")
    got = SystematicReview(RegistryScan(), Science(), Broken(), None).review("which libraries", "adopt or build", weight="quick", today=DAY, intent_id="terminal")
    assert "web search failed" in got["investigation"]["limitations"] and got["investigation"]["decisions"].startswith("all: defer: no results came back")
    assert got["gaps"] == []
    assert got["source_failed"] is True and got["search_failures"] == ["web search: down"]     # the reason reaches the caller, which can tell a failed search from an empty one


def test_a_model_may_screen_and_write_the_synthesis_and_its_failure_changes_nothing():
    calls = []

    def ask(prompt):
        calls.append(prompt)
        return '{"drop": [{"id": "i1", "reason": "x"}]}' if "drop" in prompt else '{"known": "k.", "contested": "c.", "unknown": "u."}'
    with_model = arm(ask).review("which terminal UI libraries are adoptable", "adopt or build", weight="standard", today=DAY, intent_id="terminal", use_model=True)
    assert len(calls) == 2 and with_model["investigation"]["synthesis_known"] == "k." and "judged not to bear on the question" in with_model["screened_out"]
    failing = arm(lambda prompt: "not json").review("which terminal UI libraries are adoptable", "adopt or build", weight="standard", today=DAY, intent_id="terminal", use_model=True)
    assert failing["investigation"]["synthesis_known"].startswith(("Supported", "Nothing"))


def test_the_baseline_returns_a_record_that_lacks_the_standard():
    got = RegistryResearch(RegistryScan(), Science()).review("which terminal UI libraries are adoptable", "adopt", today=DAY, intent_id="terminal")
    assert len(got["gaps"]) >= 8 and any("has no criteria" in g for g in got["gaps"])


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        csv.writer(handle).writerows([header] + rows)


def test_due_lists_reviews_experiments_and_registry_areas_past_their_dates(tmp_path, monkeypatch):
    h = tmp_path / "hubofhubs"
    write(h / "a" / "investigations.csv", ["investigation_id", "question", "links", "size", "refresh_on", "status", "done_on"],
          [["r-old", "q?", "solution:s1", "standard", "2026-11-01", "open", "2026-08-01"], ["r-new", "q2?", "area:fresh", "standard", "2027-01-01", "open", "2026-11-01"],
           ["r-done", "q3?", "", "quick", "2026-10-01", "superseded", "2026-09-01"]])
    write(h / "a" / "experiments.csv", ["experiment_id", "research_question", "links", "status", "reevaluate_time"], [["x-1", "focus", "solution:s1", "running", "2026-11-05"]])
    write(h / "registry" / "hubs.csv", ["area", "seat", "last_researched", "candidate_hubs"],
          [["stale_area", "s2", "2026-06-01", "A;B"], ["fresh", "s3", "2026-07-01", ""], ["recent", "s4", "2026-11-01", ""], ["never", "s5", "", ""]])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", h / "registry")
    got = investigation_store.due(DAY, tmp_path)
    assert [(d["kind"], d["id"]) for d in got] == [("registry-area", "never"), ("registry-area", "stale_area"), ("investigation", "r-old"), ("experiment", "x-1")]
    assert all(d["request"] and "days_overdue" in d for d in got)
    assert got[1]["days_overdue"] == (__import__("datetime").date(2026, 11, 10) - __import__("datetime").date(2026, 6, 1)).days - 90
    assert investigation_store.standing_schedule()["cadence"] == "weekly" and investigation_store.standing_schedule()["name"] == investigation_store.WEEKLY


def test_investigations_stored_under_the_older_file_and_column_names_are_still_read_and_carried_over(tmp_path, monkeypatch):
    h = tmp_path / "hubofhubs"
    write(h / "registry" / "research.csv", ["research_id", "question", "links", "size", "refresh_on", "status", "done_on"],
          [["r-old", "q?", "solution:s1", "standard", "2026-11-01", "open", "2026-08-01"]])
    write(h / "registry" / "hubs.csv", ["area", "seat", "last_researched", "candidate_hubs"], [])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", h / "registry")
    assert [(d["kind"], d["id"]) for d in investigation_store.due(DAY, tmp_path)] == [("investigation", "r-old")]
    investigation_store.store(run(links=["solution:terminal-experience"]), h / "registry")
    rows = list(csv.DictReader(open(h / "registry" / "investigations.csv")))
    assert [r["investigation_id"] for r in rows][0] == "r-old" and "research_id" not in rows[0]
    assert investigation_store.finding_investigation({"area": "x", "research_id": "r-own"}) == "r-own"


def test_an_experiment_with_the_older_field_names_is_still_due(tmp_path, monkeypatch):
    h = tmp_path / "hubofhubs"
    write(h / "a" / "experiments.csv", ["experiment_id", "focus", "links", "status", "reevaluate_on"], [["x-old", "old focus", "", "running", "2026-11-05"]])
    write(h / "registry" / "hubs.csv", ["area", "seat", "last_researched", "candidate_hubs"], [])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", h / "registry")
    got = investigation_store.due(DAY, tmp_path)
    assert [(d["id"], d["question"], d["due_on"]) for d in got] == [("x-old", "old focus", "2026-11-05")]


def test_a_stored_review_is_found_from_its_finding_and_supersedes_the_earlier_one(tmp_path, monkeypatch):
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", tmp_path / "registry")
    first = run(links=["area:terminal", "solution:terminal-experience"], today="2026-10-01")
    second = run(links=["area:terminal", "solution:terminal-experience"], today=DAY)
    investigation_store.store(first, tmp_path / "registry")
    investigation_store.store(second, tmp_path / "registry")
    rows = list(csv.DictReader(open(tmp_path / "registry" / "investigations.csv")))
    assert [r["status"] for r in rows] == ["superseded", "open"] and len(list(csv.DictReader(open(tmp_path / "registry" / "investigation_items.csv")))) == 2 * len(second["items"])
    monkeypatch.setattr(investigation_store,"files", lambda root, name: [tmp_path / "registry" / name])
    assert investigation_store.finding_investigation({"area": "terminal", "date_researched": DAY}) == second["investigation"]["investigation_id"]
    assert investigation_store.finding_investigation({"area": "terminal", "date_researched": "2026-01-01"}) == ""


def test_a_finding_names_its_review_and_old_rows_fall_back_to_area_and_date(tmp_path, monkeypatch):
    folder = tmp_path / "registry"
    write(folder / "hub_findings.csv", ["finding_id", "area", "date_researched", "summary"],
          [["HF-1", "terminal", DAY, "new"], ["HF-2", "terminal", "2026-01-01", "older day"], ["HF-3", "other", DAY, "other area"]])
    monkeypatch.setattr("hubofhubs.the_world.learning.research_freshness_reader.registry.DATA", folder)
    got = run(links=["area:terminal", "solution:terminal-experience"])
    rid = investigation_store.store(got, folder)
    rows = {r["finding_id"]: r for r in csv.DictReader(open(folder / "hub_findings.csv"))}
    assert rows["HF-1"]["investigation_id"] == rid and rows["HF-2"]["investigation_id"] == "" and rows["HF-3"]["investigation_id"] == "" and rows["HF-3"]["summary"] == "other area"
    assert list(rows["HF-1"])[-1] == "investigation_id" and investigation_store.link_findings(rid, got["investigation"], folder) == 0
    monkeypatch.setattr(investigation_store,"files", lambda root, name: [folder / name])
    assert investigation_store.finding_investigation(rows["HF-1"]) == rid
    assert investigation_store.finding_investigation({"area": "terminal", "date_researched": DAY}) == rid and investigation_store.finding_investigation(rows["HF-3"]) == ""
    assert investigation_store.finding_investigation({"area": "x", "investigation_id": "r-own"}) == "r-own"


def test_the_record_agrees_with_the_libraries_own_checker():
    library = pytest.importorskip("esoi.understanding.solution_consideration.investigations")
    got = run(weight="standard", links=["solution:terminal-experience"])
    row = dict(got["investigation"], intent_id="terminal")
    assert library.row_problems(row, got["items"]) == []


def test_the_weekly_refresh_is_standing_work_proactivity_reads():
    from hubofhubs.the_intelligence.proactivity.triggers import CalendarAndEvents
    schedule = investigation_store.standing_schedule(last_run="2026-11-02T09:00:00Z")
    due = CalendarAndEvents().due([schedule], now="2026-11-10T09:00:00Z")
    assert [t["schedule"] for t in due] == [investigation_store.WEEKLY] and due[0]["request"] == schedule["request"]
    assert CalendarAndEvents().due([investigation_store.standing_schedule(last_run="2026-11-10T08:00:00Z")], now="2026-11-10T09:00:00Z") == []


def stored(tmp_path, **changes):
    """A stored investigation (and its items) beside a registry folder of ``tmp_path``, as ``review_store.store`` writes it; returns the root to pass."""
    folder = tmp_path / "hubofhubs" / "registry"
    investigation_store.store(run(root=tmp_path, reuse=False, **changes), folder)
    return tmp_path


def test_an_investigation_always_names_a_solution_and_records_a_fallback(tmp_path):
    given = run(root=tmp_path)
    assert given["solution_link"] == {"solution": "terminal-experience", "source": "links", "fallback": False}
    from_request = run(root=tmp_path, links=["area:terminal"], solution_id="web-search")
    assert from_request["investigation"]["links"] == "area:terminal;solution:web-search" and from_request["solution_link"]["source"] == "request"
    top = run(root=tmp_path, links=[])
    assert top["investigation"]["links"] == "solution:" + investigation_store.TOP_SOLUTION and top["solution_link"]["fallback"] is True
    assert "filed under the top solution" in top["investigation"]["limitations"] and "filed under the top solution" not in given["investigation"]["limitations"]
    assert top["gaps"] == []


def test_a_row_with_no_solution_link_is_advice_not_a_failure():
    got = run()
    row = dict(got["investigation"], links="area:terminal")
    assert any("links name no solution" in g for g in inv.gaps(row, got["items"]))
    assert not any("links name no solution" in g for g in got["gaps"])


def test_ancestors_come_from_the_intent_that_holds_the_solution():
    assert investigation_store.ancestors("the-learning") == ["the-world"]
    assert investigation_store.ancestors("model-tier-chooser")[-1] == "the-world" and investigation_store.ancestors("the-world") == []


def test_what_was_looked_into_is_read_for_a_solution_and_its_ancestors(tmp_path):
    root = stored(tmp_path, links=["solution:the-world"])
    assert [r["linked_to"] for r in investigation_store.investigations_for("the-learning", True, DAY, root)] == ["the-world"]
    assert investigation_store.investigations_for("the-learning", False, DAY, root) == []
    assert investigation_store.investigations_for("the-world", False, DAY, root)[0]["fresh"] == "yes"
    assert arm().investigations_for("the-learning", today=DAY, root=root)


def test_a_fresh_investigation_of_the_same_question_is_reused_without_a_search(tmp_path):
    root = stored(tmp_path, links=["solution:the-world"])
    got = run(root=root, links=["solution:the-learning"])
    assert got["reused"] is True and got["queries"] and got["investigation"]["investigation_id"] == investigation_store.rows(root, "investigations.csv")[0]["investigation_id"]
    assert got["items"] and got["extends"] == "" and got["investigation"]["done_on"] == DAY
    arm_without_search = SystematicReview(RegistryScan(), None, None, None)
    assert arm_without_search.review(**dict(question="which terminal UI libraries are adoptable", decision="adopt or build", weight="quick", today=DAY, root=root,
                                            links=["solution:the-learning"]))["reused"] is True


def test_a_stale_or_smaller_investigation_is_extended_by_a_new_search(tmp_path):
    root = stored(tmp_path, today="2026-08-01")
    first_id = investigation_store.rows(root, "investigations.csv")[0]["investigation_id"]
    got = run(root=root)
    assert got["reused"] is False and got["extends"] == first_id and f"extends {first_id} (stale" in got["investigation"]["limitations"]
    smaller = run(root=stored(tmp_path / "second"), weight="standard")
    assert smaller["reused"] is False and "it was a smaller review" in smaller["investigation"]["limitations"]
    assert run(root=stored(tmp_path / "third"), reuse=False)["reused"] is False


def test_the_top_solution_is_the_overall_solution_the_top_intent_names():
    """The solution an investigation falls back to is the one the top intent's record names as its overall solution, not a second copy of the answer."""
    from esoi.structure.intent_registry.records import overall_solution
    root = Path(__file__).resolve().parents[4]
    with open(root / "esoi" / "intent.csv", newline="", encoding="utf-8") as handle:
        top = list(csv.DictReader(handle))[0]
    assert top["overall_solution_id"] == investigation_store.TOP_SOLUTION and overall_solution(top) == investigation_store.TOP_SOLUTION
