"""Objectives: a goal rolls up to its parent, a met objective is no longer live, a request is placed under the live objective it serves with its path, and the
bound arm shows what the roll-up adds. Nothing here calls a model."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.api import Objectives  # noqa: E402
from hubofhubs.the_intelligence.higher_mind.objectives.hierarchy import FlatList, RolledUp  # noqa: E402

TREE = [{"id": "trip", "title": "Walk the coastal path", "done_when": [{"text": "the walk is finished", "met": False}]},
        {"id": "boots", "title": "Buy walking boots", "parent": "trip", "done_when": [{"text": "boots are bought", "met": True}]},
        {"id": "maps", "title": "Print the route maps", "parent": "trip", "done_when": [{"text": "three maps are printed", "met": False}]}]


def states(arm, objectives=TREE):
    return {r["id"]: (r["depth"], r["state"], r["progress"]) for r in arm.current(objectives=objectives)}


def test_a_goal_rolls_up_to_its_parent_and_the_flat_list_does_not():
    assert states(RolledUp()) == {"trip": (0, "in progress", 0.3333), "boots": (1, "met", 1.0), "maps": (1, "not started", 0.0)}
    assert states(FlatList())["trip"] == (0, "not started", 0.0)


def test_a_parent_is_met_only_when_every_criterion_and_child_is():
    done = [dict(o, done_when=[dict(c, met=True) for c in o["done_when"]]) for o in TREE]
    assert states(RolledUp(), done)["trip"] == (0, "met", 1.0)


def test_an_objective_with_no_criteria_is_met_only_when_it_says_so():
    assert states(RolledUp(), [{"id": "a", "title": "Tidy up"}])["a"][1] == "not started"
    assert states(RolledUp(), [{"id": "a", "title": "Tidy up", "met": True}])["a"][1] == "met"


def test_a_request_is_placed_under_the_live_objective_with_its_path_from_the_top():
    found = RolledUp().place("Where do I print the route maps?", objectives=TREE)
    assert (found["objective"], found["path"]) == ("maps", ["trip", "maps"])
    assert FlatList().place("Where do I print the route maps?", objectives=TREE)["objective"] == ""     # it reads only the top level


def test_a_met_objective_is_not_live_and_a_request_sharing_no_word_names_none():
    assert RolledUp().place("Buy walking boots", objectives=TREE[1:2])["objective"] == ""
    assert RolledUp().place("What is the capital of Peru?", objectives=TREE) == {"objective": "", "path": [], "score": 0, "reason": "the request shares no word with a live objective"}


def test_a_cycle_and_an_unknown_parent_are_listed_not_lost():
    cyclic = [{"id": "x", "title": "First", "parent": "y"}, {"id": "y", "title": "Second", "parent": "x"}, {"id": "z", "title": "Third", "parent": "gone"}]
    assert [r["id"] for r in RolledUp().current(objectives=cyclic)] == ["z", "x", "y"]


def test_both_arms_satisfy_the_seat():
    assert isinstance(RolledUp(), Objectives) and isinstance(FlatList(), Objectives)
