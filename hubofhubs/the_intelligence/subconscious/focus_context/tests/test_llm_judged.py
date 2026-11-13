"""Focus Context, the judged arm: a fast-tier judge decides which candidate notes bear on the request; a word count only orders the candidates. Scripted asks, no model."""
import json
import logging
import re

from hubofhubs.the_consciousness.ai_session_experience.session_events import Capabilities, Finished, RunStarted
from hubofhubs.the_intelligence.subconscious.focus_context.arms import ConfiguredFocusContext, LlmJudgedFocusContext
from hubofhubs.the_intelligence.subconscious.focus_context.grounded import Grounded
from hubofhubs.the_intelligence.subconscious.focus_context.settings import ContextSettings
from hubofhubs.the_intelligence.subconscious.focus_context.tests.test_focus_context import NOTES

TIME_NOTE = {"id": "g-time", "title": "Sowing time", "text": "Sow at the same time every morning", "affinity_tags": ["focus:garden"], "timestamp": "2026-09-01"}


def numbers_where(prompt, *words):
    """The numbers of the listed notes whose line holds one of ``words`` (a stand-in judge's reading; the arm itself never does this)."""
    return [int(n) for n, line in re.findall(r"^\[(\d+)\] (.*)$", prompt, re.M) if any(w in line.lower() for w in words)]


def judge_saying(*words, calls=None):
    def ask(prompt):
        if calls is not None:
            calls.append(prompt)
        return json.dumps({"relevant": numbers_where(prompt, *words)})
    return ask


def test_only_the_notes_the_judge_names_reach_the_brief_and_a_none_answer_adds_nothing():
    got = LlmJudgedFocusContext(ask=judge_saying("tomato")).gather("what do my notes say about tomatoes?", NOTES, focus="garden", scope=["team:mine"])
    assert got.ids and all("tomato" in (n.title + n.text).lower() for n in got.notes) and "x-secret" not in got.ids
    none = LlmJudgedFocusContext(ask=judge_saying()).gather("What time is it?", NOTES + [TIME_NOTE], focus="garden")
    assert none.ids == [] and none.brief == "" and none.line == ""


def test_a_stray_shared_word_is_a_candidate_not_a_pick():
    prompts = []
    got = LlmJudgedFocusContext(ask=judge_saying(calls=prompts)).gather("What time is it?", NOTES + [TIME_NOTE], focus="garden")
    assert prompts and "Sowing time" in prompts[0]          # the ranking offered it to the judge, generously
    assert got.ids == []                                    # the judge, not the word, decided


def test_both_views_must_name_a_note():
    state = {"n": 0}

    def ask(prompt):
        state["n"] += 1
        return json.dumps({"relevant": [1, 2]}) if "Would a person" in prompt else json.dumps({"relevant": [2]})
    arm = LlmJudgedFocusContext(ask=ask)
    got = arm.gather("my garden", NOTES, focus="garden")
    assert len(got.ids) == 1 and state["n"] == 2 * arm.review["pages"]          # two views per page; only the note both views named is kept


def test_the_fence_holds_before_the_judge_sees_anything():
    prompts = []
    LlmJudgedFocusContext(ask=judge_saying("tomato", calls=prompts)).gather("tomatoes", NOTES, focus="garden", scope=["team:mine"])
    assert prompts and "neighbour" not in prompts[0].lower() and "Garden tomatoes of a neighbour" not in prompts[0]


def test_a_broken_judge_adds_nothing_and_says_so(caplog):
    def boom(prompt):
        raise TimeoutError("slow")
    for ask in (boom, lambda prompt: "no json here", lambda prompt: json.dumps({"relevant": "all"})):
        with caplog.at_level(logging.ERROR, logger="hubofhubs.focus_context.judge"):
            arm = LlmJudgedFocusContext(ask=ask)
            got = arm.gather("what do my notes say about tomatoes?", NOTES, focus="garden")
        assert got.ids == [] and got.brief == "" and arm.failure
    assert "adding nothing" in caplog.text
    baseline = ConfiguredFocusContext().gather("what do my notes say about tomatoes?", NOTES, focus="garden")
    assert baseline.ids                                      # the lexical picks exist and still never leak through a failed judge


def test_no_model_for_the_tier_is_a_loud_failure_with_nothing_added(monkeypatch, caplog):
    import sys
    arm = LlmJudgedFocusContext()
    monkeypatch.setattr(sys.modules[type(arm.judge).__module__], "fast_ask", lambda tier, on_usage=None: (_ for _ in ()).throw(RuntimeError("no model for the fast tier")))
    with caplog.at_level(logging.ERROR, logger="hubofhubs.focus_context.judge"):
        got = arm.gather("my garden", NOTES, focus="garden")
    assert got.ids == [] and "no model" in arm.failure and "adding nothing" in caplog.text


def test_numbers_outside_the_list_are_ignored():
    got = LlmJudgedFocusContext(ask=lambda prompt: json.dumps({"relevant": [0, 99, "x", 1]})).gather("my garden", NOTES, focus="garden")
    assert len(got.ids) == 1


class Fake:
    name, capabilities = "fake", Capabilities()

    def __init__(self):
        self.goals = []

    def start(self, goal, sink, resume_session_id=""):
        self.goals.append(goal)
        sink(RunStarted(goal=goal, harness="fake"))
        return Finished(outcome="met")

    def control(self, control):
        return False


def test_the_grounded_harness_uses_the_judge_and_a_failed_judge_leaves_the_goal_alone():
    inner = Fake()
    run = Grounded(inner, ContextSettings(focus="garden", sources=(), max_notes=3), provider=lambda focus: NOTES, arm=LlmJudgedFocusContext(ask=judge_saying()))
    run.start("What time is it?", lambda e: None)
    assert inner.goals == ["What time is it?"] and run.last.ids == []

    def boom(prompt):
        raise RuntimeError("down")
    inner = Fake()
    run = Grounded(inner, ContextSettings(focus="garden", sources=(), max_notes=3), provider=lambda focus: NOTES, arm=LlmJudgedFocusContext(ask=boom))
    run.start("what do my notes say about tomatoes?", lambda e: None)
    assert inner.goals == ["what do my notes say about tomatoes?"] and any("judge failed" in p for p in run.problems)


def many_notes(count):
    return [{"id": f"n{i}", "title": f"Note {i}", "text": f"garden sowing item {i}", "affinity_tags": ["focus:garden"], "timestamp": f"2026-01-{i:02d}"} for i in range(1, count + 1)]


def test_a_request_nothing_bears_on_costs_one_small_page_not_the_store():
    from hubofhubs.the_intelligence.subconscious.focus_context.judge import PAGE_SIZE
    prompts = []
    arm = LlmJudgedFocusContext(ask=judge_saying(calls=prompts))
    got = arm.gather("What is 17 plus 25?", many_notes(40), focus="garden")
    assert got.ids == [] and arm.review == {"pages": 1, "reviewed": PAGE_SIZE, "calls": 2} and len(prompts) == 2


def test_the_review_goes_on_while_pages_hold_relevant_notes_and_stops_when_one_does_not():
    from hubofhubs.the_intelligence.subconscious.focus_context.judge import PAGE_SIZE
    # a request with no word in common ranks the notes newest first: Note 60, Note 59, ...; the first two pages and a little of the third are relevant
    relevant = [f"note {60 - i}:" for i in range(2 * PAGE_SIZE + 2)]
    arm = LlmJudgedFocusContext(ask=judge_saying(*relevant))
    got = arm.gather("zzz qqq", many_notes(60), focus="garden", max_notes=99)
    assert arm.review["pages"] == 4 and len(got.ids) == 2 * PAGE_SIZE + 2          # three pages with relevant notes, then the page of nothing ends it


def test_a_standing_note_below_stray_word_distractors_is_found_within_its_page():
    notes = many_notes(8) + [{"id": "pref", "title": "Clock habit", "text": "Answer in Pacific time on a 24-hour clock", "affinity_tags": []}]
    arm = LlmJudgedFocusContext(ask=judge_saying("pacific"))
    got = arm.gather("What time is it?", notes, focus="garden")
    assert got.ids == ["pref"] and arm.review["pages"] == 2          # the page that holds it, then the page that ends the run


def test_one_skipped_note_does_not_stop_the_review_but_a_page_of_nothing_does():
    arm = LlmJudgedFocusContext(ask=judge_saying("note 58:"))          # rank 3 of the first page: the notes above it are skipped
    got = arm.gather("zzz qqq", many_notes(60), focus="garden")
    assert got.ids == ["n58"] and arm.review["pages"] == 2
    arm = LlmJudgedFocusContext(ask=judge_saying("note 50:"))          # rank 11: behind a whole page of nothing, so never reached
    assert arm.gather("zzz qqq", many_notes(60), focus="garden").ids == [] and arm.review["pages"] == 1
