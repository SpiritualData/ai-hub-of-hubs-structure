"""The consent gate and the two-stage arm, offline: the gate is rules only, and the model is asked only when the gate is unsure."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs.consent_gate import CLEAR, FLAG, UNSURE, ConsentGate, TwoStage, judge, parse_digest  # noqa: E402
from hubofhubs.risk import build_digest  # noqa: E402


def digest(action, goal, rationale="", operations=()):
    return build_digest(user_message="do it", step=1, max_steps=5, plan_action=action, plan_goal=goal, plan_rationale=rationale,
                        operations=list(operations), operations_total=len(operations))


class Provider:
    """A planner that answers escalate_human and counts the questions it was asked."""

    def __init__(self):
        self.asked = 0

    def plan(self, prompt, *, model, tool_schema, **kwargs):
        self.asked += 1
        return {"signal": "escalate_human", "reason": "asked"}


def render(text):
    return "judge: " + text


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


def test_the_gate_alone_sends_escalate_human_for_a_flag_and_proceed_otherwise_and_calls_no_model():
    gate, provider = ConsentGate(), Provider()
    assert gate.oversee(provider, "m", digest("pay", "Wire 40")).signal == "escalate_human"
    assert gate.oversee(provider, "m", digest("execute", "Run the tidy script")).signal == "proceed" and provider.asked == 0


def test_two_stage_asks_the_model_only_when_the_gate_is_unsure():
    arm, provider = TwoStage(render=render), Provider()
    assert arm.oversee(provider, "m", digest("pay", "Wire 40")).signal == "escalate_human" and provider.asked == 0
    assert arm.oversee(provider, "m", digest("read", "Open the notes")).signal == "proceed" and provider.asked == 0
    assert arm.oversee(provider, "m", digest("execute", "Run the tidy script")).reason == "asked" and provider.asked == 1
