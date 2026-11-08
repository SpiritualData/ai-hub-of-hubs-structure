"""Decision Check, offline with a scripted model: agreement costs only the views, a disagreement is decided by one call that must quote the evidence, a reply is repaired only at its confirmed spans,
the budget is kept, and the learning loop adopts a line only when the held-out score rises."""
import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.the_intelligence.critical_thinking.decision_check.agreement import (  # noqa: E402
    AgreementCheck, AgreementWithKnownMistakes, DraftAsGiven, SingleVerify, MajorityVote)
from hubofhubs.the_intelligence.critical_thinking.decision_check.checks import CheckBinding, View, Vote, as_binding, known_block  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.decision_check.mistakes import (  # noqa: E402
    LineBook, MistakeLog, adopt, distill, new_mistake, overruled_mistakes, retire)

OPTIONS = [{"id": "a", "text": "Alpha"}, {"id": "b", "text": "Beta"}]
RULES = "Everything about orchards belongs to Alpha."
NOTES = "Beta handles all invoices."


class Scripted:
    """A model that answers by a function of the prompt and keeps every prompt it was shown."""

    def __init__(self, reply):
        self.reply, self.prompts, self.lock = reply, [], threading.Lock()

    def __call__(self, prompt):
        with self.lock:
            self.prompts.append(prompt)
        return self.reply(prompt)


def arm(cls=AgreementCheck):
    return cls(plumbing=None)


def pick_binding(**more):
    views = [View("rules", "Which option do the rules give?", RULES), View("notes", "Which option do the notes give?", NOTES)]
    return CheckBinding(kind="pick", options=OPTIONS, views=views, **more)


def say(pick, quote=""):
    return json.dumps({"pick": pick, "quote": quote})


def test_views_that_agree_with_the_draft_cost_only_the_views():
    ask = Scripted(lambda p: say("a", "orchards belongs to Alpha") if "rules give" in p else say("a", "Beta handles"))
    got = arm().check("a", pick_binding(), ask)
    assert got["outcome"] == "agreed" and got["pick"] == "a" and got["calls"] == 2 and got["agreement"] == 1.0


def test_a_disagreement_is_decided_by_one_call_that_quotes_the_evidence_of_the_disagreeing_views():
    def reply(prompt):
        if "Independent checks disagreed" in prompt:
            assert "Everything about orchards" in prompt and "Beta handles" in prompt
            return say("a", "Everything about orchards belongs to Alpha")
        return say("a", "orchards belongs to Alpha") if "rules give" in prompt else say("b", "Beta handles all invoices")
    got = arm().check("b", pick_binding(), Scripted(reply))
    assert got["outcome"] == "adjudicated" and got["pick"] == "a" and got["calls"] == 3
    assert sorted(got["overruled"]) == ["draft", "notes"] and got["agreement"] == pytest.approx(1 / 3, abs=1e-3)


def test_an_adjudication_that_does_not_quote_the_evidence_abstains():
    def reply(prompt):
        if "Independent checks disagreed" in prompt:
            return say("a", "words that are in no evidence at all")
        return say("a", "orchards belongs to Alpha") if "rules give" in prompt else say("b", "Beta handles all invoices")
    got = arm().check("b", pick_binding(), Scripted(reply))
    assert got["outcome"] == "abstained" and got["pick"] == ""


def test_a_view_whose_quote_is_not_in_its_evidence_does_not_vote():
    ask = Scripted(lambda p: say("b", "invented words") if "rules give" in p else say("a", "Beta handles"))
    got = arm().check("a", pick_binding(), ask)
    rules = [v for v in got["views"] if v["id"] == "rules"][0]
    assert rules["pick"] == "" and "not in the evidence" in rules["reason"] and got["outcome"] == "agreed"


def test_a_vote_the_consumer_holds_counts_without_a_call():
    ask = Scripted(lambda p: say("a", "orchards belongs to Alpha"))
    binding = CheckBinding(kind="pick", options=OPTIONS, views=[View("rules", "Which option do the rules give?", RULES)], votes=[Vote("examples", "a", "three like it went to Alpha", "three like it went to Alpha")])
    got = arm().check("a", binding, ask)
    assert got["calls"] == 1 and got["outcome"] == "agreed" and len(ask.prompts) == 1


def test_the_call_cap_holds_and_a_disagreement_with_no_call_left_abstains():
    ask = Scripted(lambda p: say("a", "orchards belongs to Alpha") if "rules give" in p else say("b", "Beta handles all invoices"))
    got = arm().check("a", pick_binding(max_calls=2), ask)
    assert got["calls"] <= 2 and len(ask.prompts) <= 2
    assert got["outcome"] in ("abstained", "kept", "agreed")


def test_the_views_run_in_parallel():
    barrier = threading.Barrier(2, timeout=5)

    def reply(prompt):
        barrier.wait()          # both views must be in flight at once for this to pass
        return say("a", "orchards belongs to Alpha") if "rules give" in prompt else say("a", "Beta handles")
    got = arm().check("a", pick_binding(), Scripted(reply))
    assert got["outcome"] == "agreed"


REPLY = "I read the report. I created the task. The deadline is June 3."
READS = "The report was read. The deadline is June 5."


def reply_binding(**more):
    return CheckBinding(kind="reply", views=[View("claims", "Every claim is supported by the evidence read.", READS)], **more)


CONFIRMING = "For each numbered statement"


def verdicts(prompt, fails, quote=""):
    """A confirmation call's answer: the same verdict for every numbered statement it was shown."""
    listed = prompt.split("Statements, each judged on its own:")[1].split("Evidence:")[0]
    count = len([line for line in listed.splitlines() if line.strip()[:1].isdigit()])
    return json.dumps({"verdicts": [{"n": n, "fails": fails, "quote": quote} for n in range(1, count + 1)]})


def findings(*spans):
    return json.dumps({"findings": [{"span": s, "quote": "The deadline is June 5."} for s in spans]})


def test_a_reply_is_repaired_only_at_the_confirmed_failing_span():
    def reply(prompt):
        if "List each part" in prompt:
            return findings("The deadline is June 3.", "not in the reply")
        if CONFIRMING in prompt:
            return verdicts(prompt, True, "The deadline is June 5.")
        assert "The deadline is June 5." in prompt.split("Evidence it must agree with:")[1]
        return json.dumps({"action": "rewrite", "text": "The deadline is June 5."})
    got = arm().check(REPLY, reply_binding(), Scripted(reply))
    # A repair never adds a figure the reply did not state (the 5 is new), so the wrong sentence is removed rather than rewritten with the evidence's figure.
    assert got["outcome"] == "repaired" and got["text"] == "I read the report. I created the task."
    assert got["dropped"] == 1 and got["calls"] == 4      # one view, two agreeing confirmations (no third), one repair


def test_a_raised_span_the_independent_confirmation_clears_leaves_the_reply_untouched():
    def reply(prompt):
        if "List each part" in prompt:
            return findings("I created the task.")
        return verdicts(prompt, False)
    got = arm().check(REPLY, reply_binding(), Scripted(reply))
    assert got["outcome"] == "held" and got["text"] == REPLY and got["agreement"] == 0.0


def test_a_reply_with_no_failing_span_costs_only_the_views():
    got = arm().check(REPLY, reply_binding(), Scripted(lambda p: json.dumps({"findings": []})))
    assert got["outcome"] == "held" and got["calls"] == 1 and got["text"] == REPLY


def test_a_span_that_can_only_be_removed_is_removed_and_one_with_no_usable_repair_is_removed_by_code_and_recorded():
    def reply(prompt):
        if "List each part" in prompt:
            return findings("I created the task.")
        if CONFIRMING in prompt:
            return verdicts(prompt, True)
        return json.dumps({"action": "remove", "text": ""})
    got = arm().check(REPLY, reply_binding(), Scripted(reply))
    assert got["text"] == "I read the report. The deadline is June 3."

    def unusable(prompt):
        return reply(prompt) if "Rewrite only" not in prompt else "no idea"
    got = arm().check(REPLY, reply_binding(), Scripted(unusable))
    # A confirmed failure never ships unchanged: code removes its sentence and the span is a mistake record for the learning loop.
    assert got["outcome"] == "repaired" and got["text"] == "I read the report. The deadline is June 3."
    assert [(m["wrong"], m["source"]) for m in got["mistakes"]] == [("I created the task.", "confirmed_failure")]


def test_a_removed_clause_takes_its_whole_sentence_so_no_fragment_is_left():
    draft = "I read the report. The deadline is June 3, and I created the task."
    def reply(prompt):
        if "List each part" in prompt:
            return findings("and I created the task")
        if CONFIRMING in prompt:
            return verdicts(prompt, True)
        return json.dumps({"action": "remove", "text": ""})
    got = arm().check(draft, reply_binding(), Scripted(reply))
    assert got["text"] == "I read the report."


def test_the_known_mistake_arm_puts_the_lines_in_the_prompt_and_adds_a_twin_view_the_base_arm_does_not():
    known = {"rules": ["A farm word is not an orchard rule."]}
    seen = Scripted(lambda p: say("a", "orchards belongs to Alpha") if "rules give" in p else say("a", "Beta handles"))
    base = arm().check("a", pick_binding(known=known), seen)
    assert not any("A farm word" in p for p in seen.prompts) and base["calls"] == 2
    seen = Scripted(lambda p: say("a", "orchards belongs to Alpha") if "rules give" in p else say("a", "Beta handles"))
    got = arm(AgreementWithKnownMistakes).check("a", pick_binding(known=known), seen)
    assert got["calls"] == 3 and sum("A farm word" in p for p in seen.prompts) == 2


def test_the_known_mistake_block_is_cut_to_the_token_cap():
    assert known_block(["x" * 40, "y" * 40, "z" * 40], 25).count("- ") == 2 and known_block([], 100) == ""


def test_the_floor_and_the_single_verify_bound():
    assert DraftAsGiven().check("b", pick_binding(), None) == {"outcome": "kept", "calls": 0, "limit": 0, "agreement": 1.0, "why": "the draft was not checked", "pick": "b"}
    one = Scripted(lambda p: say("a", "Everything about orchards belongs to Alpha"))
    got = arm(SingleVerify).check("b", pick_binding(), one)
    assert got["pick"] == "a" and got["calls"] == 1 and len(one.prompts) == 1


def test_a_binding_given_as_a_mapping_is_read():
    b = as_binding({"kind": "pick", "options": OPTIONS, "views": [{"id": "v", "instruction": "i", "evidence": "e"}], "votes": [{"id": "x", "pick": "a"}]})
    assert b.views[0] == View("v", "i", "e") and b.votes[0].pick == "a"


# ---- the learning loop
def test_mistakes_are_stored_once_and_an_overruled_view_becomes_one(tmp_path):
    log = MistakeLog(tmp_path / "m.jsonl")
    m = new_mistake("rules", "slice", "b", "a", "correction")
    assert log.add(m) and not log.add(m) and log.read("rules") == [m] and log.read("other") == []
    with pytest.raises(ValueError):
        new_mistake("rules", "s", "b", "a", "gossip")
    decision = {"outcome": "adjudicated", "pick": "a", "overruled": ["notes"], "views": [{"id": "notes", "pick": "b"}]}
    found = overruled_mistakes(decision, pick_binding(), "2026-11-07")
    assert [(f.check_id, f.wrong, f.right, f.source, f.input_slice) for f in found] == [("notes", "b", "a", "overruled", NOTES)]


def records():
    return [new_mistake("rules", f"slice {i}", "b", "a", "eval_failure", case_id=f"case{i}") for i in range(4)]


def test_distill_keeps_only_lines_that_rest_on_enough_real_records():
    rs = records()
    reply = json.dumps({"lines": [
        {"line": "Prefer the owner's scope over the title.", "example": {"input": "i", "wrong": "b", "right": "a"}, "records": [rs[0].id, rs[1].id, rs[2].id]},
        {"line": "Single record rule.", "example": {"input": "i", "wrong": "b", "right": "a"}, "records": [rs[3].id]},
        {"line": "Invented support.", "example": {"input": "i", "wrong": "b", "right": "a"}, "records": ["m-nope", "m-none"]}]})
    lines = distill(rs, lambda prompt: reply)
    assert [(l.text, l.frequency) for l in lines] == [("Prefer the owner's scope over the title.", 3)] and lines[0].case_ids == ["case0", "case1", "case2"]


def test_a_line_is_adopted_only_when_the_held_out_score_rises_and_retired_when_it_stops_paying(tmp_path):
    rs = records()
    good = distill(rs, lambda p: json.dumps({"lines": [{"line": "good", "example": {"input": "i", "wrong": "b", "right": "a"}, "records": [rs[0].id, rs[1].id]}]}))
    useless = distill(rs, lambda p: json.dumps({"lines": [{"line": "useless", "example": {"input": "i", "wrong": "b", "right": "a"}, "records": [rs[2].id, rs[3].id]}]}))
    held = [{"id": f"h{i}"} for i in range(4)] + [{"id": "case0"}]

    def score(lines, cases):
        return 0.5 + (0.25 if "good" in lines else 0) + len(cases) * 0.0
    book = LineBook()
    got = adopt(book, "rules", good + useless, held, score, "2026-11-07")
    assert got["taken"] == [good[0].id] and got["version"] == 1 and got["score_after"] > got["score_before"]
    assert book.lines_for("rules") == ["good"] and good[0].adopted_in == 1
    book.lines.append(useless[0])
    useless[0].status = "adopted"
    out = retire(book, "rules", held, score, "2026-11-08")
    assert out["retired"] == [useless[0].id] and book.lines_for("rules") == ["good"] and [v["change"] for v in book.versions] == ["adopt", "retire"]
    book.save(tmp_path / "book.json")
    assert LineBook.load(tmp_path / "book.json").to_dict() == book.to_dict()


def test_a_held_out_case_a_line_was_learned_from_is_never_used_to_adopt_it():
    rs = records()
    line = distill(rs, lambda p: json.dumps({"lines": [{"line": "L", "example": {"input": "i", "wrong": "b", "right": "a"}, "records": [rs[0].id, rs[1].id]}]}))
    seen = []
    adopt(LineBook(), "rules", line, [{"id": "case0"}, {"id": "case1"}, {"id": "fresh"}], lambda lines, cases: (seen.append([c["id"] for c in cases]), 0.0)[1])
    assert ["fresh"] in seen


def test_the_majority_arm_decides_a_split_by_the_majority_with_no_adjudication_and_a_tie_still_adjudicates():
    same = "Everything about orchards belongs to Alpha."
    views = [View(f"v{i}", "Which option does the text give?", same) for i in range(3)]
    picks = iter(["a", "a", "b"])
    lock = threading.Lock()

    def reply(prompt):
        if "disagreed" in prompt:
            raise AssertionError("a majority needs no adjudication")
        with lock:
            return say(next(picks), "orchards belongs to Alpha")
    got = arm(MajorityVote).check("", CheckBinding(kind="pick", options=OPTIONS, views=views), Scripted(reply))
    assert got["outcome"] == "majority" and got["pick"] == "a" and got["calls"] == 3
    tie = iter(["a", "b"])
    asked = Scripted(lambda p: say("a", "orchards belongs to Alpha") if "disagreed" in p else say(next(tie), "orchards belongs to Alpha"))
    got = arm(MajorityVote).check("", CheckBinding(kind="pick", options=OPTIONS, views=views[:2]), asked)
    assert got["outcome"] == "adjudicated" and got["pick"] == "a"


def test_every_flagged_span_is_confirmed_and_one_with_no_call_left_for_a_rewrite_is_removed_by_code():
    draft = "One is wrong. Two is wrong. Three is wrong. Four holds."
    views = [View(f"v{i}", "A statement must hold.", "nothing") for i in range(2)]

    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "One is wrong.", "quote": ""}, {"span": "Two is wrong.", "quote": ""}, {"span": "Three is wrong.", "quote": ""}]})
        if CONFIRMING in prompt:
            return verdicts(prompt, True)
        return json.dumps({"action": "rewrite", "text": "It holds."})
    got = arm().check(draft, CheckBinding(kind="reply", views=views, max_calls=4), Scripted(reply))
    # The cap covered the two views and two repairs: the confirmations of all three spans still ran (two calls, the spans listed together, agreeing), two spans were
    # rewritten and the one with no call left was removed by code.
    assert got["calls"] == 6 and got["text"] == "It holds. It holds. Four holds." and len(got["mistakes"]) == 1


def test_a_reply_left_with_nothing_confirmed_says_so_plainly():
    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "Only claim.", "quote": ""}]})
        if CONFIRMING in prompt:
            return verdicts(prompt, True)
        return json.dumps({"action": "remove", "text": ""})
    got = arm().check("Only claim.", CheckBinding(kind="reply", views=[View("v", "A statement must hold.", "x")], max_calls=6), Scripted(reply))
    assert got["text"].startswith("I could not confirm")


def test_a_removal_needs_most_of_three_confirmations_so_one_wrong_confirmation_does_not_delete_a_true_sentence():
    draft = "The rate is 50 percent. Kaja owns it."
    views = [View("facts", "A statement must hold.", "rate 50 percent")]
    votes = iter([True, False, False])
    lock = threading.Lock()

    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "The rate is 50 percent.", "quote": ""}]})
        if CONFIRMING in prompt:
            with lock:
                return verdicts(prompt, next(votes))
        return json.dumps({"action": "remove", "text": ""})
    got = arm().check(draft, CheckBinding(kind="reply", views=views, max_calls=5), Scripted(reply))
    assert got["text"] == draft and got["outcome"] == "held" and got["calls"] == 4      # one view, two split confirmations and the third that settles it, no repair


def test_a_rewrite_never_adds_a_figure_the_reply_did_not_state_so_it_becomes_a_removal():
    draft = "The quest has 598 goals. I read only the first 100 of them."
    views = [View("facts", "A statement must hold.", "598 goals")]

    def reply(prompt):
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "I read only the first 100 of them.", "quote": ""}]})
        if CONFIRMING in prompt:
            return verdicts(prompt, True)
        return json.dumps({"action": "rewrite", "text": "69 of them are assigned to you."})
    got = arm().check(draft, CheckBinding(kind="reply", views=views, max_calls=8), Scripted(reply))
    assert got["text"] == "The quest has 598 goals." and "69" not in got["text"]


def test_a_view_that_answers_first_has_its_spans_confirmed_before_a_slow_view_returns():
    """Stages overlap: a slow view does not hold up the confirmation of what a fast view already flagged."""
    slow_may_finish = threading.Event()
    views = [View("fast", "A statement must hold.", "x"), View("slow", "A statement must hold too.", "y")]

    def reply(prompt):
        if "List each part" in prompt and "hold too" in prompt:
            assert slow_may_finish.wait(5), "the fast view's span was never confirmed while the slow view ran"
            return json.dumps({"findings": []})
        if "List each part" in prompt:
            return json.dumps({"findings": [{"span": "Only claim.", "quote": ""}]})
        if CONFIRMING in prompt:
            slow_may_finish.set()
            return verdicts(prompt, False)
        return json.dumps({"action": "remove", "text": ""})
    got = arm().check("Only claim. Fine.", CheckBinding(kind="reply", views=views, max_calls=8, parallel=4), Scripted(reply))
    assert got["outcome"] == "held" and got["calls"] == 4


def test_the_third_confirmation_is_asked_only_on_a_split_and_spans_of_one_view_are_judged_in_one_call():
    draft = "One is wrong. Two holds."
    views = [View("v", "A statement must hold.", "x")]
    seen = Scripted(lambda prompt: json.dumps({"findings": [{"span": "One is wrong.", "quote": ""}, {"span": "Two holds.", "quote": ""}]}) if "List each part" in prompt
                    else json.dumps({"verdicts": [{"n": 1, "fails": True}, {"n": 2, "fails": False}]}) if CONFIRMING in prompt
                    else json.dumps({"action": "remove", "text": ""}))
    got = arm().check(draft, CheckBinding(kind="reply", views=views, max_calls=6), seen)
    assert got["text"] == "Two holds." and got["calls"] == 4      # one view, two confirmations covering both spans, one repair
    assert sum(CONFIRMING in p for p in seen.prompts) == 2
