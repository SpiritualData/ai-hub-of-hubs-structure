"""Goal Completion's stop decision: the rule, the arms, the one that is selected and the composition that resolves what the person stated. No model call."""
import json
from pathlib import Path

from hubofhubs.the_intelligence.critical_thinking.goal_completion import stop_rule
from hubofhubs.the_intelligence.critical_thinking.goal_completion.goal_completion import EvidenceStandard, FastTierStop, IndependentReview, NonEmpty, PragmaticStop
from hubofhubs.the_consciousness.representatives.stop_limits import resolve_stop_limits

CASES = Path(__file__).resolve().parents[5] / "evaluation" / "goal_completion" / "cases.json"


def it(metric=None, verdict=False, changed=1, spend=1.0, missing=()):
    return {"verdict": verdict, "metric": metric, "changed": changed, "spend_usd": spend, "seconds": 60.0, "missing": list(missing)}


def decide(iterations, **rest):
    return stop_rule.decide(dict({"iterations": iterations, "metric": {"better": "higher", "target": 1.0}, "ceiling": {"spend_usd": 20.0, "seconds": 14400.0}}, **rest))


def test_the_five_decisions_with_their_reasons_and_facts():
    assert decide([it(0.9, verdict=True)])["decision"] == "stop_met"
    assert decide([it(0.3), it(0.6)])["decision"] == "continue"
    flat = decide([it(0.6), it(0.61), it(0.61)])
    assert flat["decision"] == "stop_not_worth_it" and flat["code"] == "plateau" and "gain_share" in flat["facts"]
    leftover = decide([it(0.4, spend=9.0), it(0.6, spend=9.0, missing=["the last two tests"])])
    assert leftover["decision"] == "stop_good_enough" and leftover["left"] == "the last two tests" and leftover["code"] == "ceiling_spend"
    asked = decide([it(0.5)], needs_human="a signature")
    assert asked["decision"] == "ask" and asked["continue"] is False and asked["left"] == "a signature"


def test_what_the_person_stated_outranks_the_default_and_policy_bounds_it():
    stalled = [it(0.6), it(0.6), it(0.6)]
    assert decide(stalled)["decision"] == "stop_not_worth_it"
    assert decide(stalled, stated={"keep_going_until": "all green", "until_reached": False})["decision"] == "continue"
    assert decide(stalled, stated={"keep_going_until": "all green", "until_reached": False}, policy={"forbids_iteration": True})["decision"] == "stop_good_enough"
    assert decide([it(0.5)], stated={"one_pass": True})["code"] == "person_limit"
    assert decide([it(0.5, spend=9.0)] * 2, stated={"keep_going_until": "all green", "until_reached": False})["decision"] == "ask"      # a ceiling is raised by the person, not overridden


def test_a_milestone_already_reached_stops_and_a_claim_of_success_is_never_a_verdict():
    assert decide([it(0.3), it(0.5)], milestone={"reached": True})["code"] == "milestone_reached"
    claimed = [dict(it(0.3), claimed_met=True), dict(it(0.6), claimed_met=True)]
    assert decide(claimed)["decision"] == "continue"


def test_the_independent_reviewer_reads_the_outcome_and_not_the_verdict_it_was_handed():
    gap = {"text": "Processed.", "coverage": {"processed": 200, "total": 344}}
    history = {"goal": "g", "done_standard": "every entry was processed", "iterations": [dict(it(0.5, verdict=True), outcome=gap)],
               "ceiling": {"spend_usd": 20.0, "seconds": 14400.0}}
    assert PragmaticStop().decide_stop(history)["decision"] == "stop_met"
    assert IndependentReview().decide_stop(history)["decision"] == "continue"
    bare = dict(history, done_standard="")
    assert IndependentReview().decide_stop(bare)["decision"] == "stop_met"      # no done-standard to read the outcome against: the check's verdict stands


def test_the_baselines_are_what_they_say():
    assert EvidenceStandard().decide_stop({"iterations": [it(0.6), it(0.6), it(0.6)]})["decision"] == "continue"       # stop only when met: it never stops a plateau
    assert NonEmpty().decide_stop({"iterations": [it(0.1), it(0.9)]})["decision"] == "stop_good_enough"                # a fixed cap: stops converging work


def test_the_fast_tier_arm_asks_the_model_and_falls_back_to_the_rule_on_a_reply_that_is_not_a_decision():
    history = {"iterations": [it(0.6), it(0.6), it(0.6)], "metric": {"better": "higher", "target": 1.0}}
    said = FastTierStop(None, ask=lambda prompt: json.dumps({"decision": "stop_not_worth_it", "reason": "flat"}))
    assert said.decide_stop(history)["decision"] == "stop_not_worth_it" and said.decide_stop(history)["code"] == "model"
    assert FastTierStop(None, ask=lambda prompt: "I think we should go on").decide_stop(history)["code"] == "fallback_rule"
    assert FastTierStop(None, ask=lambda prompt: "{\"decision\": \"stop whenever\"}").decide_stop(history)["decision"] == "stop_not_worth_it"
    assert FastTierStop.PAID is True


def test_the_scripted_cases_are_balanced_and_the_selected_arm_answers_every_one():
    cases = [c for c in json.loads(CASES.read_text()) if c["kind"] == "stop"]
    kinds = {c["expect"] for c in cases}
    assert len(cases) >= 40 and kinds == set(stop_rule.DECISIONS)
    arm = IndependentReview()
    assert [c["id"] for c in cases if arm.decide_stop(c["args"]["history"])["decision"] != c["expect"]] == []
    assert stop_rule.selected_stop_decider() is not None


def test_limits_come_from_the_representative_guidance_and_judgment_and_only_narrow():
    limits = resolve_stop_limits(
        representative={"preferences": {"iteration": {"max_iterations": 4}}, "authority": {"max_iterations": 3}},
        guidance={"iteration_policy": {"max_iterations": 2, "forbids_iteration": False}},
        judgment={"decision": "ask", "reason": "a signature"}, stated={"keep_going_until": "all green"})
    assert limits["policy"] == {"max_iterations": 2} and limits["needs_human"] == "a signature"
    assert limits["stated"] == {"max_iterations": 4, "keep_going_until": "all green"} and limits["sources"] == ["representative", "stated", "guidance", "judgment-calls"]
    assert resolve_stop_limits(stated={"one_pass": True}, representative={"preferences": {"iteration": {"one_pass": False, "stop": True}}})["stated"] == {"stop": True, "one_pass": True}
    assert resolve_stop_limits() == {"stated": {}, "policy": {}, "needs_human": "", "sources": []}
    assert resolve_stop_limits(guidance={"iteration_policy": {"forbids_iteration": True}})["policy"] == {"forbids_iteration": True}
