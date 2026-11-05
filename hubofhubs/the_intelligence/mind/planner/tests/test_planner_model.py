"""The model planner, offline with a scripted model: it turns a model's JSON plan into pieces with a sub-goal and one tool, and refuses a plan it cannot use."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.mind.planner.model_planner import ModelPlanner, PlanError, parse_pieces  # noqa: E402
from hubofhubs.the_intelligence.mind.planner.planning import CueRouter  # noqa: E402


class Plumbing:
    def __init__(self, reply):
        self.reply, self.asked = reply, []

    def ask(self, prompt, tier=""):
        self.asked.append((prompt, tier))
        return self.reply


def test_the_model_planner_returns_pieces_with_a_sub_goal_and_one_tool_each():
    plumbing = Plumbing('[{"piece": "find the newest stable release", "tool": "web-search"}, {"piece": "summarise what the notes say", "tool": "none"}]')
    pieces = ModelPlanner(plumbing).plan("Tell me the newest stable release and summarise the notes", context={"view": "[file notes.md] x"})
    assert [(p["piece"], p["tool"]) for p in pieces] == [("find the newest stable release", "web-search"), ("summarise what the notes say", "")]
    assert pieces[0]["sub_goal"]["done_standard"].startswith("a response that addresses")
    assert "[file notes.md] x" in plumbing.asked[0][0] and "em dashes" in plumbing.asked[0][0]


def test_a_request_with_no_cue_word_gets_the_right_worker_from_the_model_and_none_from_the_cue_router():
    for request, tool in (("Rewrite the clause in the contract file", "file-editing"), ("Name the maintainer of that compiler", "web-search")):
        assert CueRouter().plan(request)[0]["tool"] == ""                      # no cue word, so no worker
        assert ModelPlanner(Plumbing('[{"piece": "' + request + '", "tool": "' + tool + '"}]')).plan(request)[0]["tool"] == tool


@pytest.mark.parametrize("reply", ["not json", "[]", '{"piece": "x"}', '[{"piece": "x", "tool": "magic"}]', '[{"piece": "", "tool": "none"}]'])
def test_a_reply_that_is_not_a_usable_plan_raises_and_is_never_guessed_at(reply):
    with pytest.raises(PlanError):
        parse_pieces(reply)


def test_a_fenced_reply_is_read():
    assert parse_pieces('```json\n[{"piece": "a", "tool": "none"}]\n```') == [{"piece": "a", "tool": ""}]
