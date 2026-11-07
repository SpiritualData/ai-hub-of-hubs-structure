"""Pursuing an unmet goal: the decisions of the bounded replan, over a stub check and a stub attempt."""
from hubofhubs.the_intelligence.critical_thinking.pursuit import BoundedReplan

READ = {"name": "search", "kind": "read", "cost_seconds": 5}
WRITE = {"name": "post", "kind": "write", "cost_seconds": 5}


def check(outcome):
    return {"met": outcome == "good", "reason": "the transcript is not used"}


def test_a_met_draft_is_sent_without_any_attempt():
    calls = []
    got = BoundedReplan().pursue("g", "d", "good", lambda step: calls.append(step) or {}, [READ], None, None, check)
    assert got["status"] == "met" and calls == []


def test_an_unmet_draft_is_replanned_with_reads_only_before_it_is_sent():
    offered = []

    def attempt(step):
        offered.append(step)
        return {"outcome": "good", "means_used": step["means"]}
    got = BoundedReplan().pursue("g", "d", "bad", attempt, [READ, WRITE], None, None, check)
    assert got["status"] == "met_after_replan" and offered[0]["means"] == ["search"] and offered[0]["read_only"] is True


def test_a_write_reported_by_an_attempt_is_discarded_and_recorded():
    got = BoundedReplan().pursue("g", "d", "bad", lambda step: {"outcome": "good", "writes": ["post"]}, [READ], None, None, check)
    assert got["status"] == "unmet_reported" and got["outcome"] == "bad" and got["ignored_writes"] == [["post"]]


def test_long_work_can_continue_in_the_background_and_adds_no_line():
    lines = []
    got = BoundedReplan().pursue("g", "d", "bad", lambda step: {}, [dict(READ, cost_seconds=60)], {"background": True}, lines.append, check)
    assert got["status"] == "continuing" and lines == [] and got["message"] == "" and got["continue"]["means"] == ["search"]


def test_an_unrecoverable_goal_adds_no_line_and_keeps_the_checkers_words_for_logs():
    got = BoundedReplan().pursue("g", "d", "bad", lambda step: {"outcome": "still bad", "means_used": ["search"]}, [READ], None, None, check)
    assert got["status"] == "unmet_reported" and got["message"] == "" and got["tried"] == ["search"] and "transcript" in got["missing"]


def test_a_question_to_the_person_is_terminal_and_satisfied_so_nothing_is_pursued_announced_or_added():
    calls, lines = [], []
    got = BoundedReplan().pursue("g", "d", "which topic?", lambda step: calls.append(step) or {}, [dict(READ, cost_seconds=60)], {"background": True}, lines.append,
                                 lambda outcome: {"met": False, "awaiting_person": True, "reason": "the person supplies the missing piece"})
    assert got["status"] == "awaiting_person" and got["met"] is True and got["message"] == "" and got["outcome"] == "which topic?"
    assert calls == [] and lines == [] and "continue" not in got
