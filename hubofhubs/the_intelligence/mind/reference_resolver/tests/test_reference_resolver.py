"""Resolve a Reference, offline with a scripted model: a match is one candidate offered, a near-miss is an abstain, and an unusable model reply raises."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.mind.reference_resolver.resolving import (  # noqa: E402
    ExactMatch, ModelJudged, ReferenceNotSettled, SharedWords)

PEOPLE = [{"id": "u1", "name": "Ann Lee", "aliases": ["ann.lee@example.org"]}, {"id": "u2", "name": "Joanne Park"}, {"id": "u3", "name": "Ann Marie Ortiz"}]
GOALS = [{"id": "g1", "name": "Newsletter subscribers import cleanup"}, {"id": "g2", "name": "Subscribers survey results"}]


def test_exact_match_takes_an_id_a_whole_name_an_alias_and_whole_words_of_one_name():
    arm = ExactMatch()
    assert arm.resolve("u2", PEOPLE)["id"] == "u2"
    assert arm.resolve("ann lee", PEOPLE)["id"] == "u1"
    assert arm.resolve("ann.lee@example.org", PEOPLE)["id"] == "u1"
    assert arm.resolve("Park", PEOPLE)["id"] == "u2"


@pytest.mark.parametrize("phrase", ["Ann", "Joan", "Priya", "Lee Park", "", "the"])
def test_exact_match_abstains_on_two_that_fit_a_part_of_a_word_an_unknown_and_an_empty_phrase(phrase):
    answer = ExactMatch().resolve(phrase, PEOPLE)
    assert answer["outcome"] == "abstain" and answer["id"] == "" and answer["reason"]


def test_two_unrelated_goals_that_share_words_with_the_request_are_abstained_on_but_not_by_shared_words():
    phrase = "Send the spring newsletter to subscribers"
    assert ExactMatch().resolve(phrase, GOALS)["outcome"] == "abstain"
    assert SharedWords().resolve(phrase, GOALS)["outcome"] == "match"      # the old way overwrites; this is why it is only the bound


class Asked:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.reply


def test_model_judged_uses_the_hand_in_call_and_takes_a_candidate_offered_or_none():
    ask = Asked('{"id": "g1"}')
    assert ModelJudged(None).resolve("the goal about tidying the imported list", GOALS, ask=ask)["id"] == "g1"
    assert len(ask.prompts) == 1 and "g2 | Subscribers survey results" in ask.prompts[0] and "not the same thing" in ask.prompts[0]
    answer = ModelJudged(None).resolve("renew the domain", GOALS, ask=Asked('{"id": "NONE"}'))
    assert answer["outcome"] == "abstain"


@pytest.mark.parametrize("reply", ["not json", '{"id": "g9"}', "{}", '{"id": ""}'])
def test_model_judged_raises_on_a_reply_that_names_no_candidate_offered(reply):
    with pytest.raises(ReferenceNotSettled):
        ModelJudged(None).resolve("x", GOALS, ask=Asked(reply))


def test_model_judged_with_no_candidates_makes_no_call():
    ask = Asked('{"id": "g1"}')
    assert ModelJudged(None).resolve("x", [], ask=ask)["outcome"] == "abstain" and ask.prompts == []
