"""The cascade's structural half: what escalates, how a verdict folds back, and the middle-out cut."""
from hubofhubs.orchestrate.cascade import (
    apply_review, escalation_spec, should_escalate, truncate_keep_both_ends, user_goal_fallback,
)
from hubofhubs.orchestrate.plan import PlanDecision

GOAL, QUESTION = "A default goal.", "A default question?"


def review(cheap, raw):
    return apply_review(cheap, raw, default_goal=GOAL, default_question=QUESTION)


def test_escalation_spec_parses_levels_and_actions_and_drops_the_rest():
    assert escalation_spec("low,,action:not_real,bananas,ACTION:Read") == {
        "levels": frozenset({"low"}), "actions": frozenset({"read"})}
    assert escalation_spec(None) == escalation_spec("") == {"levels": frozenset(), "actions": frozenset()}


def test_should_escalate_on_an_action_or_a_reported_confidence_only():
    assert should_escalate(PlanDecision(action="read"), escalation_spec("action:read"))
    assert should_escalate(PlanDecision(action="answer", confidence="low"), escalation_spec("low"))
    assert not should_escalate(PlanDecision(action="answer"), escalation_spec("low,medium,high"))
    assert not should_escalate(PlanDecision(action="read", confidence="low"), escalation_spec(""))
    assert should_escalate(PlanDecision(action="answer", confidence="low"), frozenset({"low"}))


def test_truncate_keeps_both_ends_and_the_limit():
    text = "START" + "x" * 1000 + "END"
    out = truncate_keep_both_ends(text, 80, "\n...\n")
    assert len(out) <= 80 and out.startswith("START") and out.endswith("END")
    assert truncate_keep_both_ends("short", 500) == "short"
    assert truncate_keep_both_ends("abc", 0) == "" and truncate_keep_both_ends("abcdef", 3, "\n...\n") == "abc"


def test_user_goal_fallback_is_never_empty():
    assert user_goal_fallback(PlanDecision(action="deep", goal="g"), default_goal=GOAL) == "g"
    assert user_goal_fallback(PlanDecision(action="deep", deferred_deep={"goal": "d"}), default_goal=GOAL) == "d"
    assert user_goal_fallback(PlanDecision(action="deep"), default_goal=GOAL) == GOAL


def test_a_reviewer_that_agrees_or_is_unusable_leaves_the_decision_the_same_object():
    cheap = PlanDecision(action="read", reads=[{"a": 1}])
    assert review(cheap, None) is cheap and review(cheap, {"action": "bogus"}) is cheap
    assert review(cheap, {"action": "read"}) is cheap


def test_a_correction_keeps_the_fields_it_did_not_speak_to():
    cheap = PlanDecision(action="read", reads=[{"a": 1}], model_tier="t", confidence="low", deep_target="x")
    deep = review(cheap, {"action": "deep"})
    assert (deep.action, deep.goal, deep.model_tier, deep.confidence, deep.deep_target) == ("deep", GOAL, "t", "low", "x")
    assert review(PlanDecision(action="deep", goal="g"), {"action": "read"}).action == "answer"
    confirm = review(cheap, {"action": "confirm"})
    assert confirm.confirm_question == QUESTION and confirm.model_tier == "t"


def test_an_answer_that_hands_off_carries_the_goal_and_brief():
    got = review(PlanDecision(action="deep", goal="g", deep_brief="b"), {"action": "answer", "hand_off": True, "rationale": "r"})
    assert got.action == "answer" and got.deferred_deep == {"goal": "g", "brief": "b", "rationale": "r"}
