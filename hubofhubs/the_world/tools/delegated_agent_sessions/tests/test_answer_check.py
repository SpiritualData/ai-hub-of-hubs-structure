"""The answer check: the final answer held to the person's own words, one resume on a fail, the helper's brief and the stop decision reading the same words."""
import json

from hubofhubs.the_world.tools.delegated_agent_sessions import answer_check as check, native_runner
from hubofhubs.the_world.tools.delegated_agent_sessions import general_helper as helpers
from hubofhubs.the_world.tools.delegated_agent_sessions.run_ceilings import stop_aware
from hubofhubs.the_world.tools.delegated_agent_sessions.tests.test_native_runner import records, runner_for

ASKED = "Use a cheap helper to find something interesting about my garden notes and then give your own opinion on what it finds"


def verdict_text(parts, about=True, invents=False, subject="the garden notes"):
    return json.dumps({"parts": [{"part": p, "met": m, "reason": "r"} for p, m in parts], "subject": subject, "about_subject": about, "invents_task": invents})


GOOD = verdict_text([("use a helper", True), ("find something about the garden notes", True), ("give an opinion", True)])
DRIFT = verdict_text([("use a helper", True), ("find something about the garden notes", False), ("give an opinion", False)], about=False, invents=True)


def test_the_pass_is_computed_here_and_never_taken_from_the_model():
    said_pass = json.dumps({"pass": True, "parts": [{"part": "a", "met": False, "reason": "no"}], "about_subject": True, "invents_task": False})
    assert check.parse_verdict(said_pass)["passed"] is False
    assert check.parse_verdict(GOOD)["passed"] is True
    assert check.parse_verdict(verdict_text([("a", True)], about=False))["passed"] is False
    assert check.parse_verdict(verdict_text([("a", True)], invents=True))["passed"] is False
    assert check.parse_verdict("not json") is None and check.parse_verdict('{"parts": []}') is None


def test_the_check_is_given_only_the_original_input_and_the_answer():
    seen = []
    check.judge(ASKED, "The answer text.", lambda system, prompt: seen.append((system, prompt)) or GOOD)
    system, prompt = seen[0]
    assert ASKED in prompt and "The answer text." in prompt and "REQUEST" in prompt
    assert "garden" not in system


def test_nothing_to_judge_or_a_failing_call_is_no_opinion():
    assert check.judge("", "answer", lambda s, p: GOOD) is None and check.judge(ASKED, " ", lambda s, p: GOOD) is None
    assert check.judge(ASKED, "answer", lambda s, p: 1 / 0) is None


def test_the_steer_is_built_from_the_original_words_and_the_unmet_parts():
    steer = check.steer_message(ASKED, check.parse_verdict(DRIFT))
    assert steer.startswith("The request was: " + ASKED)
    assert "Your answer did not find something about the garden notes" in steer and "Your answer did not give an opinion" in steer
    assert "was not about the garden notes" in steer and "Answer it directly" in steer and "say so and look again" in steer
    assert "—" not in steer


def test_a_passing_answer_is_not_resumed():
    resumed = []
    got = check.run_round(ASKED, "good answer", lambda s, p: GOOD, lambda message: resumed.append(message) or "x")
    assert not resumed and got["verdict"]["passed"] and not got["resumed"] and got["answer"] == "good answer"


def test_a_drifting_answer_is_resumed_once_and_the_new_answer_is_checked_and_kept():
    replies = iter([DRIFT, GOOD])
    resumed, told = [], []
    got = check.run_round(ASKED, "answer about another project", lambda s, p: next(replies), lambda message: resumed.append(message) or "answer about the notes",
                          emit=lambda phase, text, data: told.append(phase))
    assert len(resumed) == 1 and resumed[0].startswith("The request was: " + ASKED)
    assert got["resumed"] and got["answer"] == "answer about the notes" and got["after"]["passed"]
    assert told == ["answer_check", "hub_resume", "answer_check"]


def test_a_limit_or_a_ceiling_stops_the_resume_and_says_why():
    resumed = []
    got = check.run_round(ASKED, "drift", lambda s, p: DRIFT, lambda message: resumed.append(message), allowed=lambda: "ceiling_reached")
    assert not resumed and got["skipped"] == "ceiling_reached" and not got["resumed"] and got["answer"] == "drift"


def test_a_failed_resume_keeps_the_first_answer_and_no_model_is_no_opinion():
    got = check.run_round(ASKED, "first", lambda s, p: DRIFT, lambda message: None)
    assert got["resumed"] and got["answer"] == "first" and got["after"] is None
    assert check.run_round(ASKED, "first", None, lambda m: "x")["skipped"] == "no model for the check"
    assert check.run_round(ASKED, "first", lambda s, p: "garbage", lambda m: "x")["skipped"].startswith("the check gave no readable")


def test_the_tier_comes_from_the_role_table_and_a_missing_row_is_the_fast_tier():
    asked = []
    check.answer_ask(lambda tier: asked.append(tier) or None, tier_of=lambda role, requested="": (_ for _ in ()).throw(KeyError(role)))
    assert asked == ["fast"]
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
    assert role_tiers.tier_for(check.ROLE) == "fast"


def test_the_helper_carries_the_original_input_verbatim_and_the_main_session_is_told_to_write_the_answer():
    defined = helpers.helper_definition("m", ASKED)["helper"]
    assert ASKED in defined["prompt"] and "something else" in defined["prompt"]
    assert ASKED not in helpers.helper_definition("m")["helper"]["prompt"]
    note = helpers.helper_note(3)
    assert "word for word" in note and "material, not the answer" in note and "your own answer" in note


def test_the_stop_decision_gets_the_original_input_as_its_goal():
    seen = []
    decide = stop_aware(lambda history: seen.append(history) or {"decision": "stop_good_enough", "continue": False})
    decide({"rounds": [{"findings": 1}], "findings": ["x"], "goal": ASKED})
    assert seen[0]["goal"] == ASKED


# --- the native runner: the real wiring on the fake CLI of its own tests -------------------------------------------------------------------

class Scripted:
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, system, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def test_the_native_runner_resumes_the_same_session_once_with_a_steer_from_the_original_input(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, check_answer=True)
    runner.answer_asker = Scripted(DRIFT, GOOD)
    got = runner.run_goal(goal=ASKED, brief="")
    launches = [r for r in records(log) if "argv" in r]
    messages = [r["message"] for r in records(log) if "message" in r]
    assert len(launches) == 2 and "--resume" in launches[1]["argv"]
    assert "The request was: " + ASKED in messages[1] and "Answer it directly" in messages[1]
    assert got.answer_check["resumed"] and got.answer_check["verdict"]["passed"] is False and got.answer_check["after"]["passed"]
    assert ASKED in runner.answer_asker.prompts[0] and runner.original_input == ASKED


def test_a_passing_answer_makes_one_check_and_no_resume(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, check_answer=True)
    runner.answer_asker = Scripted(GOOD)
    got = runner.run_goal(goal=ASKED, brief="")
    assert len([r for r in records(log) if "argv" in r]) == 1 and got.answer_check["verdict"]["passed"] and not got.answer_check["resumed"]


def test_the_resume_limit_applies_to_the_answer_check(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch, check_answer=True)
    runner.answer_asker = Scripted(DRIFT)
    monkeypatch.setattr(native_runner, "MAX_RESUMES", 0)
    got = runner.run_goal(goal=ASKED, brief="")
    assert len([r for r in records(log) if "argv" in r]) == 1 and got.answer_check["skipped"] == "resume_cap" and not got.answer_check["resumed"]


def test_the_answer_check_is_off_when_asked(tmp_path, monkeypatch):
    runner, log, _work = runner_for(tmp_path, monkeypatch)
    runner.answer_asker = Scripted(DRIFT)
    got = runner.run_goal(goal=ASKED, brief="")
    assert not hasattr(got, "answer_check") and runner.answer_asker.prompts == []


def test_the_run_offers_its_helper_the_original_input(tmp_path, monkeypatch):
    runner, _log, _work = runner_for(tmp_path, monkeypatch)
    given = []
    real = helpers.helper_definition
    monkeypatch.setattr(helpers, "helper_definition", lambda model, original="", notes="": given.append(original) or real(model, original, notes))
    runner.run_goal(goal=ASKED, brief="")
    assert given and given[0] == ASKED


# --- the saved notes reach the helper through the run context, and the person's words stay the reference ---------------------------------------

def test_the_helper_prompt_carries_the_saved_notes_with_the_rule_beside_the_original_input():
    block = "What is already known about practice, saved by the person:\n\n[1] Daily log\nMeditated at dawn."
    prompt = helpers.helper_definition("m", ASKED, block)["helper"]["prompt"]
    assert ASKED in prompt and "[1] Daily log" in prompt and "notes first" in prompt and "never fill the gap" in prompt
    assert "ALREADY SAVED" not in helpers.helper_definition("m", ASKED)["helper"]["prompt"]


def test_a_wrapper_attaches_the_context_to_the_runner_under_it_and_a_resumed_turn_keeps_the_first_message():
    from hubofhubs.the_intelligence.subconscious.focus_context.grounded import Grounded
    from hubofhubs.the_intelligence.subconscious.focus_context.settings import ContextSettings
    from hubofhubs.the_world.tools.delegated_agent_sessions.run_context import RunContext, attach

    class Runner:
        run_context = None

        def run_goal(self, **kwargs):
            return None

    class Inner:
        name, capabilities = "fake", None

        def __init__(self):
            self.runner, self.goals = Runner(), []

        def start(self, goal, sink, resume_session_id=""):
            self.goals.append(goal)

        def control(self, control):
            return False
    inner = Inner()
    notes = [{"id": "n1", "title": "Daily log", "text": "Meditated at dawn.", "affinity_tags": ["focus:practice"], "overview": True}]
    from hubofhubs.the_intelligence.subconscious.focus_context.arms import ConfiguredFocusContext
    wrapped = Grounded(inner, ContextSettings(focus="practice", sources=(), max_notes=3), provider=lambda focus: notes, arm=ConfiguredFocusContext())
    wrapped.start(ASKED, lambda event: None)
    context = inner.runner.run_context
    assert context.original == ASKED and "Daily log" in context.notes and "Background only" not in context.notes     # the notes, without the main session's rule
    assert inner.goals[0].startswith(ASKED + "\n\n")                                                                     # the goal the harness is started with carries the brief
    wrapped.start("and now shorter", lambda event: None, "sess-1")
    assert inner.runner.run_context.original == ""
    assert attach(object(), RunContext()) is False


def test_the_native_runner_reads_the_person_s_words_and_the_notes_from_the_context_not_from_the_goal_text(tmp_path, monkeypatch):
    from hubofhubs.the_world.tools.delegated_agent_sessions.run_context import RunContext
    runner, _log, _work = runner_for(tmp_path, monkeypatch)
    runner.run_context = RunContext(original=ASKED, notes="[1] Daily log")
    given = []
    real = helpers.helper_definition
    monkeypatch.setattr(helpers, "helper_definition", lambda model, original="", notes="": given.append((original, notes)) or real(model, original, notes))
    runner.run_goal(goal=ASKED + "\n\nWhat is already known about practice:\n\n[1] Daily log", brief="")
    assert given and given[0] == (ASKED, "[1] Daily log") and runner.original_input == ASKED
