"""Intuition arms: what comes to mind unasked, from the closeness of wording and from what was taken for similar requests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.subconscious.intuition.co_taken import CoTaken  # noqa: E402
from hubofhubs.the_intelligence.subconscious.intuition.interface import Intuiting  # noqa: E402
from hubofhubs.the_intelligence.subconscious.intuition.nearest_cards import NearestCards  # noqa: E402


class Held:
    def __init__(self, texts):
        self.texts = texts

    def corpus(self):
        return dict(self.texts)


CARDS = {"roses": "Prune roses in late winter before new growth", "tools": "Sharpen and oil the secateurs", "tax": "Quarterly tax payment due dates"}


def test_both_arms_satisfy_the_interface():
    assert isinstance(NearestCards(Held(CARDS)), Intuiting) and isinstance(CoTaken(Held(CARDS)), Intuiting)


def test_nearest_cards_offers_the_card_sharing_words_and_nothing_for_an_unrelated_request():
    arm = NearestCards(Held(CARDS))
    got = arm.offer("when to prune the roses")
    assert [item["id"] for item in got] == ["roses"] and got[0]["why"] == "similar" and set(got[0]) == {"id", "text", "score", "why"}
    assert arm.offer("translate this invoice into French") == []


def test_the_limit_bounds_what_is_offered():
    arm = NearestCards(Held({"a": "garden roses", "b": "garden tools", "c": "garden soil"}))
    assert len(arm.offer("garden", limit=2)) == 2 and arm.offer("garden", limit=0) == []


def test_co_taken_brings_back_a_card_with_no_shared_word_and_says_why():
    history = [{"request": "how to prune roses before spring", "taken": ["tools"], "age_days": 3}]
    got = CoTaken(Held(CARDS), history).offer("when to prune the roses")
    assert {item["id"]: item["why"] for item in got} == {"roses": "similar", "tools": "taken before"}


def test_an_old_take_fades_and_a_take_of_an_unrelated_request_does_not_count():
    history = [{"request": "prune roses", "taken": ["tools"], "age_days": 400}, {"request": "tax payment", "taken": ["tools"], "age_days": 0}]
    assert [item["id"] for item in CoTaken(Held(CARDS), history).offer("prune roses")] == ["roses"]


def test_a_taken_id_the_store_no_longer_holds_is_ignored_and_no_history_means_nearest():
    assert CoTaken(Held(CARDS), [{"request": "prune roses", "taken": ["gone"]}]).offer("prune roses") == NearestCards(Held(CARDS)).offer("prune roses")
