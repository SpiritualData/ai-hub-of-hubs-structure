"""Route a Request, offline with a scripted model and a scripted planner: the closed list of routes, the structure of the plan-derived route, and that an unusable reply raises."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.mind.request_router.routing import (  # noqa: E402
    MajorityFloor, PlanDerived, RouteError, SingleClassifier, parse_route, route_from_report)


class Plumbing:
    def __init__(self, reply):
        self.reply, self.asked = reply, []

    def ask(self, prompt, tier=""):
        self.asked.append((prompt, tier))
        return self.reply


class Planner:
    def __init__(self, pieces):
        self.pieces = pieces

    def plan(self, request, context=None, target=None, guidance=None, unmet=None):
        return self.pieces


def test_the_classifier_asks_once_with_the_view_and_returns_the_route():
    plumbing = Plumbing('{"route": "act", "reason": "asks to move a milestone"}')
    answer = SingleClassifier(plumbing).route("podcast listeners", {"view": "Milestones: podcast listeners"})
    assert answer == {"route": "act", "reason": "asks to move a milestone"}
    assert len(plumbing.asked) == 1 and "Milestones: podcast listeners" in plumbing.asked[0][0] and "em dashes" in plumbing.asked[0][0]


@pytest.mark.parametrize("reply", ["not json", "[]", '{"route": "deep"}', '{"reason": "x"}', ""])
def test_a_reply_that_is_not_a_route_from_the_list_raises_and_is_never_guessed_at(reply):
    with pytest.raises(RouteError):
        parse_route(reply)


def test_a_fenced_reply_is_read():
    assert parse_route('```json\n{"route": "draft", "reason": "text"}\n```')["route"] == "draft"


@pytest.mark.parametrize("report,route", [
    ({"needs_more": True, "reply_deliverable": True, "intent": "act"}, "clarify"),
    ({"reply_deliverable": True, "intent": "act"}, "draft"),
    ({"intent": "act"}, "act"),
    ({"worker": "file-editing", "intent": "ask"}, "act"),
    ({"worker": "web-search", "intent": "ask"}, "information"),
    ({}, "information"),
])
def test_the_route_of_a_plan_report_is_decided_by_structure(report, route):
    assert route_from_report(report)["route"] == route


def test_plan_derived_calls_the_planner_and_reads_only_the_worker_that_changes_something():
    assert PlanDerived(Planner([{"piece": "x", "tool": "file-editing"}])).route("edit it")["route"] == "act"
    assert PlanDerived(Planner([{"piece": "x", "tool": "web-search"}])).route("what is it")["route"] == "information"
    assert PlanDerived(Planner([])).route("")["route"] == "clarify"


def test_a_consumer_planner_report_can_say_draft():
    class Mine(PlanDerived):
        def report(self, request, context=None):
            return {"reply_deliverable": True}
    assert Mine(Planner([])).route("write a caption")["route"] == "draft"


def test_the_floor_always_says_information():
    assert MajorityFloor().route("anything")["route"] == "information"
