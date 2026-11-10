"""The composition's stop decision: limits resolved from Consciousness inputs, then Goal Completion's ``decide_stop`` through the step, pending when it has no arm."""
from hubofhubs.the_intelligence.critical_thinking.flow import CriticalThinkingComposition
from hubofhubs.the_intelligence.critical_thinking.goal_completion.goal_completion import PragmaticStop
from hubofhubs.the_intelligence.mind.delegation.solution_workers import work_solution
from hubofhubs.the_self.steps import DONE, PENDING

PLATEAU = {"iterations": [{"verdict": False, "metric": m, "changed": 1, "spend_usd": 1.0, "seconds": 5.0} for m in (0.6, 0.6, 0.6)],
           "metric": {"better": "higher", "target": 1.0}, "ceiling": {"spend_usd": 20.0, "seconds": 14400.0}}


def composition(goal):
    return CriticalThinkingComposition(metric=None, esoi=None, goal=goal, quality=None, decision=None, upkeep=None)


def test_the_stated_wish_and_the_policy_reach_goal_completion_as_plain_inputs():
    got = composition(PragmaticStop()).decide_stop(PLATEAU)
    assert got["decision"]["decision"] == "stop_not_worth_it" and got["steps"][0]["status"] == DONE
    kept_going = composition(PragmaticStop()).decide_stop(PLATEAU, stated={"keep_going_until": "all green"})
    assert kept_going["decision"]["decision"] == "continue" and kept_going["limits"]["stated"] == {"keep_going_until": "all green"}
    bounded = composition(PragmaticStop()).decide_stop(PLATEAU, representative={"authority": {"forbids_iteration": True}}, stated={"keep_going_until": "all green"})
    assert bounded["decision"]["decision"] == "stop_good_enough" and bounded["limits"]["policy"] == {"forbids_iteration": True}
    asked = composition(PragmaticStop()).decide_stop(PLATEAU, judgment={"decision": "ask", "reason": "a payment"})
    assert asked["decision"]["decision"] == "ask" and asked["decision"]["left"] == "a payment"


def test_a_goal_completion_with_no_arm_is_a_pending_step_and_no_decision():
    from esoi import AssemblyError

    class NoArm:
        def __getattr__(self, name):
            raise AssemblyError("goal-completion has no implementation")
    got = composition(NoArm()).decide_stop(PLATEAU)
    assert got["decision"] is None and got["steps"][0]["status"] == PENDING


def test_a_part_that_keeps_missing_the_same_thing_is_not_worked_a_third_time():
    def frame(sid):
        return {"name": sid, "approach": "a", "milestone": "m"}
    calls = []

    def work(brief):
        calls.append(brief.get("round"))
        return "same output"
    plateau = work_solution("root", frame=frame, children=lambda s, t: [], work=work, budget={"rounds": 4, "calls": 10},
                            check=lambda sid, milestone, output: {"met": False, "missing": "the table"})
    assert len(calls) == 2 and plateau.stopped.endswith("stop_not_worth_it") and plateau.status == "unmet"      # one more round for a first try, none for the same gap
    changing = work_solution("root", frame=frame, children=lambda s, t: [], work=lambda b: "x" * (b.get("round") or 1), budget={"rounds": 4, "calls": 10},
                             check=lambda sid, milestone, output: {"met": len(output) >= 3, "missing": "more", "score": len(output) / 4})
    assert changing.status == "met" and changing.calls == 3 and changing.stopped == ""
    refused = work_solution("root", frame=frame, children=lambda s, t: [], work=work, budget={"rounds": 4, "calls": 10}, stop=lambda history: {"decision": "ask", "code": "needs_human"},
                            check=lambda sid, milestone, output: {"met": False, "missing": "a login"})
    assert refused.stopped == "needs_human:ask" and refused.calls == 1
