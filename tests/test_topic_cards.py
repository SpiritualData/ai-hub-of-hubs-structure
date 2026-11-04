"""The topic-needs and orientation components, and the free topic builders: grouping, the cases and their time split, the scoring rules,
and the proof that a card per file and a single giant card both lose.

The corpus tests read Quest AI Runner at its pinned commit through ``git archive`` (as ``test_cards_from_files`` does) and are skipped,
with the reason, on a machine that has no checkout holding that commit."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evaluation"))
sys.path.insert(0, str(ROOT))

from cards_from_files import corpus as pinned  # noqa: E402
from cards_from_files.broken import one_card, one_card_per_folder, two_cards  # noqa: E402
from hubofhubs.recall import cards_from_files as file_arms  # noqa: E402
from hubofhubs.recall import cards_from_topics as topic_arms  # noqa: E402
from hubofhubs.recall import topic_clusters  # noqa: E402
from needed_set import cases as needed_cases  # noqa: E402
from needed_set import score as needed  # noqa: E402
from orientation import score as orientation  # noqa: E402


@pytest.fixture(scope="module")
def corpus():
    try:
        return pinned.load()
    except pinned.PinUnavailable as exc:
        pytest.skip(f"the pinned commits are not available here: {exc}")


def test_agglomerate_respects_the_cap_and_is_deterministic():
    weights = {}
    for a, b in [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("x", "y")]:
        topic_clusters.add_pair(weights, a, b, 1.0)
    first = topic_clusters.agglomerate(weights, cap=3)
    assert first == topic_clusters.agglomerate(dict(reversed(list(weights.items()))), cap=3)
    assert all(2 <= len(group) <= 3 for group in first) and sorted(sum(first, [])) == sorted(set(sum(first, [])))
    assert ["x", "y"] in first


def test_a_pair_below_the_weight_floor_joins_nothing():
    assert topic_clusters.agglomerate({("a", "b"): 0.4}, cap=4, min_weight=0.5) == []


def test_folder_chunks_keep_a_folder_together_and_never_leave_a_lone_tail():
    files = [f"p/f{i}.py" for i in range(9)] + ["q/only.py"]
    chunks = topic_clusters.folder_chunks(files, 4)
    assert [len(c) for c in chunks] == [3, 3, 3, 1]
    assert all(len({f.split("/")[0] for f in c}) == 1 for c in chunks)


@pytest.mark.parametrize("subject,names", [
    ("Answer a request for the person's own updates directly before the plan", False),
    ("Fix the loader in quest_ai_runner/core/orchestrator.py now", True),
    ("Rename the loader in orchestrator.py everywhere it appears", True),
    ("Make the FileContextStore ignore stale cards in every answer", True),
    ("Call `assemble` once per turn for every conversation lane", True),
    ("Keep the retry_policy steady while the lane is restarting", True),
    ("Check flush() returns before the lane supervisor stops it", True),
    ("Rework the reach judge so a quiet turn keeps its earlier verdict", False),
])
def test_the_subject_filter(subject, names):
    assert needed_cases.names_something(subject) is names


def test_the_cases_are_pinned_topic_only_and_split_in_time(corpus):
    cases, history = needed_cases.load(), needed_cases.load_history()
    assert len(cases) == 150 and all(2 <= len(c["needed"]) <= 8 and len(c["task"]) >= 30 for c in cases)
    assert not any(needed_cases.names_something(c["task"]) for c in cases)
    assert all(f in set(corpus.files) for c in cases for f in c["needed"])
    assert not {c["commit"] for c in cases} & {h["commit"] for h in history}
    assert max(h["date"] for h in history) <= min(c["date"] for c in cases)


def test_a_changed_case_file_is_a_hard_error(corpus, monkeypatch, tmp_path):
    copy = tmp_path / "cases.json"
    copy.write_text(needed_cases.CASES_FILE.read_text() + " ")
    monkeypatch.setattr(needed_cases, "CASES_FILE", copy)
    with pytest.raises(needed_cases.CasesMismatch):
        needed_cases.load()


def test_the_cases_are_never_regenerated_silently():
    with pytest.raises(needed_cases.CasesMismatch):
        needed_cases.write()


def test_the_score_rules_on_a_made_up_view():
    case = dict(task="t", needed=["a/x.py", "b/y.py"])
    cards = [["a/x.py", "b/y.py"], ["c/z.py"], ["d/w.py"], ["e/v.py"]]
    fn = lambda kind, args: dict(view=sum(cards, []), cards=cards, build=None)
    row = needed.score_case(fn, case)
    assert (row["cov1"], row["cov3"], row["ok"], row["bundled"], row["spans"]) == (1.0, 1.0, True, True, True)
    assert row["noise3"] == pytest.approx(0.5) and row["view"] == 4
    miss = needed.score_case(lambda kind, args: dict(view=["c/z.py"], cards=[["c/z.py"]], build=None), case)
    assert (miss["cov3"], miss["ok"]) == (0.0, False)


def test_the_store_cap_disqualifies_a_card_per_file(corpus):
    many = [dict(ok=True, build=dict(cards=len(corpus.files), id="x", calls=0, tokens=0, cost=0.0, seconds=0.0))]
    few = [dict(ok=True, build=dict(cards=100, id="x", calls=0, tokens=0, cost=0.0, seconds=0.0))]
    assert "cards per file" in needed.disqualify(many) and needed.disqualify(few) == ""


def test_the_orientation_rules():
    assert orientation.area_hit(["q/a/x.py", "q/a/y.py"], "q/a") and orientation.area_hit(["q/x.py"], "q/a")
    assert not orientation.area_hit(["q/b/x.py"], "q/a") and not orientation.area_hit(["x.py", "q/y.py"], "q/a")
    case = dict(task="t", target="q/a/x.py")
    row = orientation.score_case(lambda kind, args: dict(view=["z/1.py", "q/a/w.py"], cards=[["z/1.py"], ["q/a/w.py"]], build=None), case)
    assert row["folder_hit"] and not row["area_hit"]


def run(builder, module, cases=None):
    fn = module.view_function(builder, None)
    return [module.score_case(fn, case) for case in (cases or module.load_cases())]


@pytest.mark.parametrize("grouping", [one_card, two_cards, one_card_per_folder])
def test_a_giant_card_passes_no_topic_case(corpus, grouping):
    rows = run(grouping.cards, needed)
    assert sum(r["ok"] for r in rows) == 0 and max(r["view"] for r in rows) > needed.MAX_VIEW_FILES


def test_a_card_per_file_is_disqualified_whatever_it_finds(corpus):
    rows = run(file_arms.PerFileSymbols().build, needed, needed.load_cases()[:3])
    assert needed.disqualify(rows)


def test_the_history_of_the_cochange_builder_ends_before_every_test_case(corpus):
    arm = topic_arms.CochangeTopicCards()
    assert {c["commit"] for c in arm.commits}.isdisjoint(c["commit"] for c in needed.load_cases())


@pytest.mark.parametrize("arm", [topic_arms.CochangeTopicCards, topic_arms.ImportGraphTopicCards])
def test_the_free_topic_builders_keep_to_the_cap_and_are_deterministic(corpus, arm):
    cards = arm().build(str(corpus.root), corpus.files, {})
    assert cards == arm().build(str(corpus.root), corpus.files, {})
    assert len(cards) / len(corpus.files) <= needed.MAX_CARDS_PER_FILE
    assert all(len(c["files"]) <= topic_arms.CARD_CAP for c in cards)
    listed = [e["path"] for c in cards for e in c["files"]]
    assert len(listed) == len(set(listed)) and set(listed) == set(corpus.files)   # every file reachable, in one card


def test_the_iteration_how_to_matches_the_recorded_stages():
    """The how-to names the stages the metric record carries, in the same order, and only paid arm in esoi.toml is the model builder."""
    import csv
    import re
    rows = {r["metric_id"]: r for r in csv.DictReader(open(ROOT / "hubofhubs" / "recall" / "metrics.csv", newline=""))}
    stages = [s.split(" [")[0].strip() for s in rows["metric-cards-topic-needs"]["cascading_conditionals"].split(" > ")]
    assert stages == ["idea", "free", "one", "sample", "whole"]
    page = (ROOT / "docs" / "how-to" / "iterate-on-card-builders-without-repeating-model-calls.md").read_text()
    assert [m.group(1) for m in re.finditer(r"^## Stage (\d)", page, re.M)] == ["0", "1", "2"]
    assert all(f"`{name}`" in page for name in ("needed_set", "cards_from_files", "orientation", "topic_cards_replay"))
    assert re.search(r'paid_arms = \["cards_from_files/llm_topic_cards"\]', (ROOT / "esoi.toml").read_text())
    commands = rows["metric-cards-topic-needs"]["command"]
    assert "needed_set --impl cochange_topic_cards" in commands and "orientation" in rows["metric-cards-orientation"]["command"]
    assert "—" not in page   # no em dashes
