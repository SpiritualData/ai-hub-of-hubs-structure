"""Guidance: the rule gate points at one objective's next target and reading, or says nothing when the moment calls for the answer alone; the bounds do not."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.api import Guiding  # noqa: E402
from hubofhubs.the_intelligence.higher_mind.guidance.nudging import AlwaysNudge, OverlapOnly, RuleGate  # noqa: E402

RUN = {"id": "run", "name": "the 10 km race", "next_target": "complete a 15 km long run by 15 November", "reading": "longest run so far 12 km, target 15 km",
       "criteria": {"concision": 0.6}}
DRAFT = {"id": "draft", "name": "the thesis draft", "next_target": "send chapter 3 to the committee", "reading": "pages drafted 74 of 120"}


def test_the_arms_satisfy_the_interface():
    assert all(isinstance(arm(), Guiding) for arm in (RuleGate, OverlapOnly, AlwaysNudge))


def test_a_nudge_is_one_sentence_of_the_objectives_own_words_and_carries_its_criteria():
    got = RuleGate().nudge("I just finished my long run, what should I log?", [DRAFT, RUN])
    assert got["objective"] == "run" and got["quality_criteria"] == {"concision": 0.6}
    assert got["nudge"] == "Next for the 10 km race: complete a 15 km long run by 15 November (longest run so far 12 km, target 15 km)."


def test_the_gate_holds_back_for_urgent_upset_stop_unrelated_and_recently_raised():
    gate = RuleGate()
    for request in ("My run is urgent, the race entry closes in an hour", "I am so discouraged about the race", "Stop reminding me about the race",
                    "What is 18 percent of 240?"):
        assert gate.nudge(request, [RUN]) is None
    assert gate.nudge("Thanks, bye", [dict(RUN, nudged_recently=True)]) is None
    assert gate.nudge("Thanks, bye", []) is None


def test_an_open_moment_points_at_the_focused_objective_and_an_objective_without_a_target_is_skipped():
    got = RuleGate().nudge("Where do things stand?", [DRAFT, dict(RUN, in_focus=True), {"id": "bare", "name": "no target"}])
    assert got["objective"] == "run"
    assert RuleGate().nudge("Where do things stand?", [{"id": "bare", "name": "no target"}]) is None


def test_the_bounds_differ_from_the_gate_where_the_metric_says_they_should():
    assert OverlapOnly().nudge("Thanks, that is all", [RUN]) is None
    assert OverlapOnly().nudge("My race is urgent", [RUN]) is not None
    assert AlwaysNudge().nudge("Translate good morning into German.", [RUN]) is not None
