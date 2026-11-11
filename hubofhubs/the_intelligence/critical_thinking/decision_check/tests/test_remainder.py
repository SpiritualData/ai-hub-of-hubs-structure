"""What is left of a reply after a removal still reads as an answer, and a length limit removes the least needed sentences, never by position alone."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.critical_thinking.decision_check.agreement import AgreementCheck  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.decision_check.checks import CheckBinding, View  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.decision_check.remainder import (  # noqa: E402
    cohere, cohered_text, complete, dangling, figures, joined, shortened_text, units_of)


def removed(text, *gone):
    units = units_of(text)
    for u in units:
        if u.text in gone:
            u.kept = False
    return units


def test_a_pronoun_opening_right_after_a_removed_sentence_dangles():
    units = removed("The top item is the launch milestone. Its current value is 50 percent.", "The top item is the launch milestone.")
    assert dangling(units) == [1]


def test_the_same_after_a_removed_sentence_dangles_but_not_after_a_kept_one():
    text = "Sign-ups stand at 40 this week. The tracker shows the same figure. The next review is Monday."
    assert dangling(removed(text, "Sign-ups stand at 40 this week.")) == [1]
    assert dangling(units_of(text)) == []


def test_a_demonstrative_whose_noun_only_a_removed_sentence_said_dangles():
    units = removed("The release is not out. The store asked for a signing key. I have no record that key was added.", "The store asked for a signing key.")
    assert dangling(units) == [2]


def test_a_definite_description_is_not_a_back_reference():
    # "The release" opens a sentence that names its own subject; removing a later sentence that also says "release" leaves it standing.
    units = removed("The release is not out. The release track is internal only, at 0 of 100. Nothing newer is recorded.", "The release track is internal only, at 0 of 100.")
    assert dangling(units, "Is the release out?") == []


def test_a_noun_the_question_names_is_still_anchored():
    units = removed("The store asked for a key. That key is still missing.", "The store asked for a key.")
    assert dangling(units, "Is the key still missing?") == []


def test_cohere_without_a_call_removes_the_dangling_sentence_and_keeps_the_rest():
    units, how = cohere(removed("Milestone A is first. Its value is 50 percent. The owner is you.", "Milestone A is first."))
    assert how == "removed" and joined(units) == "The owner is you."


def test_cohere_takes_a_rewrite_built_from_the_remaining_words():
    def ask(prompt):
        assert "2. Its value is 50 percent of sign-ups." in prompt and "Sentences that point back to removed text: 2" in prompt
        return json.dumps({"sentences": [{"n": 2, "action": "rewrite", "text": "The value is 50 percent of sign-ups."}]})
    units = removed("The owner is you. Milestone A is first. Its value is 50 percent of sign-ups.", "Milestone A is first.")
    units, how = cohere(units, "what is first?", ask)
    assert how == "rewritten" and joined(units) == "The owner is you. The value is 50 percent of sign-ups."


def test_cohere_refuses_a_rewrite_that_adds_a_figure_or_a_name_and_removes_the_sentence():
    units = removed("The owner is you. Milestone A is first. Its value is 50 percent.", "Milestone A is first.")
    for bad in ("The value is 60 percent.", "Milestone Zeta has a value of 50 percent."):
        trial = [type(u)(u.text, u.lead, u.kept) for u in units]
        got, how = cohere(trial, "", lambda prompt, bad=bad: json.dumps({"sentences": [{"n": 2, "action": "rewrite", "text": bad}]}))
        assert joined(got) == "The owner is you."


def test_cohered_text_keeps_paragraphs_and_never_empties_the_reply():
    before = "Paid users are at 0.\n\nThe tracker shows the same figure.\n\nThe urgent item is due today."
    assert cohered_text(before, "The tracker shows the same figure.\n\nThe urgent item is due today.") == "The urgent item is due today."
    assert cohered_text("A thing is so. It holds.", "It holds.") == "It holds."


def test_figures_are_compared_by_value():
    assert figures("1,000 users on 02 May") == {"1000", "2"} and figures("1000 users on 2 May") == {"1000", "2"}


def test_shorten_keeps_the_answer_and_drops_the_least_needed_not_the_middle():
    text = ("The release is not out yet. The store listing is internal only, so release downloads are 0 of 1000. "
            "I have no record that the release blocker was cleared. I cannot see anything newer, so this may have changed.")
    got = shortened_text(text, 3, "What is the status of the release?")
    assert got.startswith("The release is not out yet.") and "release downloads are 0 of 1000" in got and "anything newer" not in got


def test_shorten_drops_a_sentence_that_repeats_an_earlier_one_first():
    text = "The task is not done. The blocker is still open. The blocker is still open, so it is not cleared. The owner is named in the goal."
    got = shortened_text(text, 3, "Is the task done and who owns it?")
    assert got == "The task is not done. The blocker is still open. The owner is named in the goal."


def test_shorten_never_cuts_a_protected_draft_and_does_not_count_it():
    draft = "Subject: Join us\n\nHi,\n\nWe are opening sign-ups. Please forward this.\n\nThanks,\nThe team"
    text = "I updated the next step. The owner is set. The step is due Friday.\n\n" + draft + "\n\nThe metric is unchanged."
    got = shortened_text(text, 2, "can you move the ads forward?", protected=[draft])
    assert draft in got and got.startswith("I updated the next step.")


def test_a_removal_in_the_reply_check_leaves_no_dangling_sentence():
    """The shape seen live: the first sentence is confirmed failing and removed, and the next opens with "Its"; the coherence call rewrites it from the remaining words."""
    draft = "Your top item is milestone A, due today. Its current value is 50 percent, read on Friday."
    views = [View("facts", "A statement must hold.", "milestone A due next week; value 50 percent read Friday")]

    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "Your top item is milestone A, due today.", "quote": ""}]})
        if "For each numbered statement" in prompt:
            return json.dumps({"verdicts": [{"n": 1, "fails": True, "quote": ""}]})
        if "point back to something that is no longer said" in prompt:
            return json.dumps({"sentences": [{"n": 1, "action": "rewrite", "text": "The current value is 50 percent, read on Friday."}]})
        return json.dumps({"action": "remove", "text": ""})
    got = AgreementCheck(plumbing=None).check(draft, CheckBinding(kind="reply", views=views, max_calls=6, question="what is the top item?"), reply)
    assert got["text"] == "The current value is 50 percent, read on Friday." and got["cohered"] == "rewritten"


def test_a_span_over_several_sentences_is_removed_whole():
    draft = "I updated the step. Joey owns it. The step is due Sunday. The draft is below."
    views = [View("facts", "A statement must hold.", "nothing")]

    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "Joey owns it. The step is due Sunday.", "quote": ""}]})
        if "For each numbered statement" in prompt:
            return json.dumps({"verdicts": [{"n": 1, "fails": True, "quote": ""}]})
        return json.dumps({"action": "remove", "text": ""})
    got = AgreementCheck(plumbing=None).check(draft, CheckBinding(kind="reply", views=views, max_calls=6), reply)
    assert got["text"] == "I updated the step. The draft is below."


def test_a_back_reference_a_few_words_in_dangles_but_a_conjunction_that_does_not():
    units = removed("The top item is milestone A. Behind it, the headline count is 0.", "The top item is milestone A.")
    assert dangling(units) == [1]
    units = removed("The owner is set. I know that the count is 0.", "The owner is set.")
    assert dangling(units) == []


def test_a_repair_that_leaves_a_fragment_removes_the_whole_sentence():
    """The shape seen live: a confirmed span "Sunday 8 November." was rewritten without its full stop and left a fragment ("The step is due this"); a sentence must stay whole, else it goes."""
    draft = "The goal is owned by Mary. The step is due Sunday 8 November. The draft is kept on the goal."
    views = [View("facts", "A statement must hold.", "the step is due this week")]

    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "Sunday 8 November.", "quote": ""}]})
        if "For each numbered statement" in prompt:
            return json.dumps({"verdicts": [{"n": 1, "fails": True, "quote": ""}]})
        return json.dumps({"action": "rewrite", "text": "this"})
    got = AgreementCheck(plumbing=None).check(draft, CheckBinding(kind="reply", views=views, max_calls=6), reply)
    assert got["text"] == "The goal is owned by Mary. The draft is kept on the goal."
    assert got["findings"][0]["action"] == "remove" and "incomplete" in got["findings"][0]["why_removed"]


def test_a_coherence_rewrite_must_be_a_complete_sentence():
    units = removed("The owner is you. Milestone A is first. Its due date is Friday.", "Milestone A is first.")
    got, how = cohere(units, "", lambda prompt: json.dumps({"sentences": [{"n": 2, "action": "rewrite", "text": "The step is due"}]}))
    assert joined(got) == "The owner is you." and how == "removed"
    assert complete("The step is due Friday.") and not complete("The step is due") and not complete("Mary ow")


def test_a_sentence_with_a_quotation_it_never_closes_is_not_complete():
    from hubofhubs.the_intelligence.critical_thinking.decision_check.remainder import complete
    assert complete('Start with "Order wax and wicks." It was due 8 November.')
    assert not complete('Start with "It was due 8 November and is now 3 days overdue.')
    assert not complete("Start with \u201cIt was due 8 November and is now 3 days overdue.")
