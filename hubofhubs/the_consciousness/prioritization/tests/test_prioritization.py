"""Prioritization: the field-reading arm orders by the stated rules, honours what the person declared or implied, explains each place and gives the metric-ready
priority; the as-given arm is the bound. Nothing here calls a model."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import hubofhubs  # noqa: E402
from hubofhubs.api import Prioritizing, Stated, ordered_ids  # noqa: E402
from hubofhubs.the_consciousness.prioritization.ordering import AsGiven, StatedFields  # noqa: E402

NOW = "2026-07-12T09:00:00Z"
KINDS = {"kind_order": ["ask", "goal", "idea"]}
ITEMS = [{"id": "idea", "kind": "idea"}, {"id": "goal-late", "kind": "goal", "deadline": "2026-09-01T00:00:00Z"},
         {"id": "goal-soon", "kind": "goal", "deadline": "2026-07-13T00:00:00Z"}, {"id": "ask", "kind": "ask", "title": "Send the numbers"}]


def order(**kw):
    kw["stated"] = dict(KINDS, **kw.get("stated", {}))
    return ordered_ids(StatedFields().prioritize(candidates=ITEMS, now=NOW, **kw)["ordered"])


def test_the_kinds_follow_the_order_the_person_gave_then_the_deadline_and_the_baseline_keeps_the_order_given():
    assert order() == ["ask", "goal-soon", "goal-late", "idea"]
    assert ordered_ids(StatedFields().prioritize(candidates=ITEMS, now=NOW)["ordered"]) == ["goal-soon", "goal-late", "idea", "ask"]      # no kind order stated: the deadline decides, undated keep their order
    assert ordered_ids(AsGiven().prioritize(candidates=ITEMS)["ordered"]) == ["idea", "goal-late", "goal-soon", "ask"]


def test_the_person_s_own_rank_puts_ranked_items_first_ascending_and_unranked_after_in_the_order_given():
    items = [{"id": "u1"}, {"id": "r2", "rank": 2}, {"id": "r0", "rank": 0}, {"id": "u2"}]
    assert ordered_ids(StatedFields().prioritize(candidates=items, now=NOW)["ordered"]) == ["r0", "r2", "u1", "u2"]


def test_the_person_s_explicit_order_comes_first_and_what_they_deferred_comes_last():
    assert order(stated={"order": ["idea", "goal-late"], "deferred": ["ask"]}) == ["idea", "goal-late", "goal-soon", "ask"]


def test_feedback_that_implies_sooner_or_later_moves_an_item_or_a_whole_kind():
    assert order(stated={"feedback": [{"about": "idea", "direction": "sooner"}]})[0] == "idea"
    assert order(stated={"feedback": [{"about": "ask", "direction": "later"}]})[-1] == "ask"
    assert order(stated={"feedback": [{"about": "goal", "direction": "later"}]}) == ["ask", "idea", "goal-soon", "goal-late"]


def test_constraints_hold_items_back_and_say_why():
    held = StatedFields().prioritize(candidates=ITEMS, now=NOW, stated=dict(KINDS, only_kinds=["ask", "goal"], not_before={"goal-late": "2027-01-01T00:00:00Z"}))
    assert ordered_ids(held["ordered"]) == ["ask", "goal-soon"]
    assert {h["id"]: h["reason"] for h in held["held"]} == {"idea": "the person limited the work to ask, goal", "goal-late": "the person said not before 2027-01-01T00:00:00Z"}
    assert held["constraints"] == [{"kind": "only_kinds", "value": ["ask", "goal"]}]


def test_a_blocked_item_follows_the_unblocked_of_its_kind_and_the_waiting_and_the_nudge_break_ties():
    items = [{"id": "b", "kind": "goal", "blocked_by": ["a"]}, {"id": "a", "kind": "goal"}, {"id": "w", "kind": "goal", "waiting": ["x", "y"]},
             {"id": "n1", "kind": "goal", "last_nudged_at": "2026-07-11T00:00:00Z"}, {"id": "n0", "kind": "goal", "last_nudged_at": "2026-07-01T00:00:00Z"}]
    got = ordered_ids(StatedFields().prioritize(candidates=items, now=NOW)["ordered"])
    assert got.index("a") < got.index("b") and got.index("w") < got.index("a") and got.index("n0") < got.index("n1")


def test_each_place_has_a_reason_and_the_weights_sum_to_one_with_the_first_weighing_most():
    out = StatedFields().prioritize(candidates=ITEMS, now=NOW, person="p", stated=KINDS)
    assert all(row["reason"] for row in out["ordered"]) and "kind ask" in out["ordered"][0]["reason"] and "due 2026-07-13" in out["ordered"][1]["reason"]
    weights = [row["metric"]["weight"] for row in out["ordered"]]
    assert weights == sorted(weights, reverse=True) and sum(weights) == pytest.approx(1.0, abs=1e-3)
    assert out["ordered"][0]["metric"]["milestone"] == "Send the numbers" and out["ordered"][1]["metric"]["due"] == "2026-07-13T00:00:00Z"


def test_quality_weights_pass_through_and_no_candidates_returns_only_the_weights():
    out = StatedFields().prioritize(stated=Stated(quality_weights={"safety": 0.4}))
    assert out["ordered"] == [] and out["quality_weights"] == {"safety": 0.4}


def test_the_seat_is_reached_by_its_id_and_by_its_typed_handle():
    got = hubofhubs.run("prioritization", {"person": "p", "candidates": ITEMS, "now": NOW, "stated": KINDS})
    assert ordered_ids(got["ordered"]) == ["ask", "goal-soon", "goal-late", "idea"]
    assert isinstance(hubofhubs.run(Prioritizing), Prioritizing)
