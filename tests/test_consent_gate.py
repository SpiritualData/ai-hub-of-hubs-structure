"""The consent gate, offline: the gate is rules only, and it sends one risk signal (high, medium or none), never a routing verdict."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs.the_intelligence.nervous_system.consent_gate import CLEAR, FLAG, UNSURE, ConsentGate, judge, parse_digest  # noqa: E402
from hubofhubs.the_intelligence.nervous_system.digest import build_digest  # noqa: E402


def digest(action, goal, rationale="", operations=()):
    return build_digest(user_message="do it", step=1, max_steps=5, plan_action=action, plan_goal=goal, plan_rationale=rationale,
                        operations=list(operations), operations_total=len(operations))


def test_the_digest_is_read_back_into_action_goal_rationale_and_operations():
    assert parse_digest(digest("pay", "Wire 40", "due today", ["[read] a -> b"])) == ("pay", "Wire 40", "due today", "1. [read] a -> b")


def test_a_consent_action_is_flagged_and_a_plain_read_is_clear():
    assert judge(digest("send_mail", "Mail the list"))[0] == FLAG
    assert judge(digest("read", "Open the notes"))[0] == CLEAR


def test_a_read_that_names_a_consent_class_and_an_unknown_action_are_unsure():
    assert judge(digest("search", "Find the refund policy"))[0] == UNSURE
    assert judge(digest("execute", "Run the tidy script"))[0] == UNSURE


def test_an_unknown_action_whose_words_or_operations_name_a_class_is_flagged_unless_it_is_the_runs_own_work():
    assert judge(digest("execute", "Delete the customer rows"))[0] == FLAG
    assert judge(digest("execute", "Run the script", operations=["[read] script -> DROP TABLE users; delete rows"]))[0] == FLAG
    assert judge(digest("execute", "Delete the scratch file made in this run"))[0] == UNSURE


def test_the_gate_sends_high_for_a_flag_medium_for_an_unsure_step_and_none_for_a_clear_one_with_no_model():
    gate = ConsentGate()
    assert gate.watch(digest("pay", "Wire 40")).severity == "high"
    assert gate.watch(digest("execute", "Run the tidy script")).severity == "medium"      # an unchecked step is never severity none
    assert gate.watch(digest("search", "Find the refund policy")).severity == "medium"
    clear = gate.watch(digest("read", "Open the notes"))
    assert clear.severity == "none" and clear.reason == ""
