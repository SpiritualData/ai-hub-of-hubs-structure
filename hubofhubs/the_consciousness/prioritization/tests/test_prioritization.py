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


ASKS = [{"id": "old", "kind": "ask", "asked_at": "2026-07-01T00:00:00Z"}, {"id": "frees-three", "kind": "ask", "unblocks": ["t1", "t2", "t3"], "effort": 5},
        {"id": "due-soon", "kind": "ask", "unblocks": ["t4"], "deadline": "2026-07-13T00:00:00Z"}]


def test_asks_come_in_the_order_of_what_they_unblock_then_the_deadline_not_the_order_they_arrived():
    out = StatedFields().prioritize(candidates=ASKS, now=NOW, subject="asks")
    assert ordered_ids(out["ordered"]) == ["frees-three", "due-soon", "old"] and out["subject"] == "asks"
    assert "frees 3 waiting items" in out["ordered"][0]["reason"]
    assert ordered_ids(AsGiven().prioritize(candidates=ASKS, subject="asks")["ordered"]) == ["old", "frees-three", "due-soon"]


def test_a_batch_limit_puts_only_that_many_asks_in_front_of_the_person_and_holds_the_rest_with_why():
    out = StatedFields().prioritize(candidates=ASKS, now=NOW, subject="asks", batch_limit=2)
    assert ordered_ids(out["ordered"]) == ["frees-three", "due-soon"]
    assert out["held"] == [{"id": "old", "rank": 3, "reason": "held for a later batch: 2 are put in front of the person at once and this one is place 3"}]
    assert sum(r["metric"]["weight"] for r in out["ordered"]) == pytest.approx(1.0, abs=1e-3)


def test_the_person_s_own_order_still_comes_before_what_an_ask_unblocks():
    out = StatedFields().prioritize(candidates=ASKS, now=NOW, subject="asks", stated={"order": ["old"]})
    assert ordered_ids(out["ordered"])[0] == "old"


MILESTONES = [{"id": "m-ship", "kind": "milestone", "solution": "s-a", "intent": "i-1", "deadline": "2026-08-01T00:00:00Z", "blocked_by": ["m-build"], "metric": 0.9},
              {"id": "m-build", "kind": "milestone", "solution": "s-a", "intent": "i-1", "deadline": "2026-07-20T00:00:00Z", "unblocks": ["m-ship"]},
              {"id": "m-done", "kind": "milestone", "solution": "s-b", "intent": "i-1", "met": "2026-06-01T00:00:00Z"},
              {"id": "m-old", "kind": "milestone", "solution": "s-b", "intent": "i-2", "ends_at": "2026-07-01T00:00:00Z"},
              {"id": "m-other", "kind": "milestone", "solution": "s-c", "intent": "i-2", "deadline": "2026-07-15T00:00:00Z"}]


def test_milestones_are_ordered_by_dependency_and_target_time_with_or_without_a_metric_and_the_met_and_ended_are_held():
    out = StatedFields().prioritize(candidates=MILESTONES, now=NOW, subject="goals")
    assert ordered_ids(out["ordered"]) == ["m-build", "m-other", "m-ship"]      # m-build has no metric value and is first: it unblocks m-ship and is due before it
    assert {h["id"] for h in out["held"]} == {"m-done", "m-old"}


def test_what_the_person_said_about_a_solution_or_intent_counts_for_its_milestones():
    out = StatedFields().prioritize(candidates=MILESTONES, now=NOW, subject="goals", stated={"order": ["s-c"]})
    assert ordered_ids(out["ordered"])[0] == "m-other"
    out = StatedFields().prioritize(candidates=MILESTONES, now=NOW, subject="goals", stated={"feedback": [{"about": "s-a", "direction": "later"}]})
    assert ordered_ids(out["ordered"]) == ["m-other", "m-build", "m-ship"]


def test_a_subject_the_seat_does_not_know_is_refused():
    with pytest.raises(ValueError):
        StatedFields().prioritize(candidates=ASKS, subject="chores")
