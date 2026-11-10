"""The ceilings shared by the runners (``run_ceilings``): defaults on, UNLIMITED explicit, a soft limit that steers once, a hard limit that stops and keeps the work
resumable, and the stop decision that gates the hub's own iteration (a review call, a repeated nudge) in the text loop. A scripted completion: no model, no network."""
from __future__ import annotations

import pytest

from hubofhubs.the_world.tools.delegated_agent_sessions import run_ceilings
from hubofhubs.the_world.tools.delegated_agent_sessions.run_ceilings import UNLIMITED, LimitWatch, history_of_rounds, stop_aware
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import run_loop
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner, as_solution_worker
from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.tests.test_solution_loop import Script, edit, folder, runner_for

CONTINUE = {"decision": "continue", "continue": True, "code": "gain_worth_cost"}
STOP = {"decision": "stop_not_worth_it", "continue": False, "code": "plateau"}


def test_every_runner_has_default_ceilings_and_unlimited_is_explicit(tmp_path):
    for runner in (SolutionLoopRunner(root=str(tmp_path), complete=lambda s, p: ""), StreamJsonGoalRunner(root=str(tmp_path))):
        assert runner.ceiling_usd == run_ceilings.DEFAULT_CEILING_USD and runner.ceiling_seconds == run_ceilings.DEFAULT_CEILING_SECONDS
        assert 0 < runner.ceiling_usd <= 100 and 3600 <= runner.ceiling_seconds <= 24 * 3600
    free = SolutionLoopRunner(root=str(tmp_path), complete=lambda s, p: "", ceiling_usd=UNLIMITED, ceiling_seconds=UNLIMITED)
    assert free.ceiling_usd is None and free.ceiling_seconds is None
    for bad in (0, -1, None, True, "lots"):
        with pytest.raises(ValueError):
            SolutionLoopRunner(root=str(tmp_path), complete=lambda s, p: "", ceiling_usd=bad)
        with pytest.raises(ValueError):
            StreamJsonGoalRunner(root=str(tmp_path), ceiling_seconds=bad)


def test_the_soft_limit_steers_the_loop_once_to_a_safe_stopping_point(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    script = Script("RUN: true\nNOTE: working", "RUN: true\nNOTE: still", "REPORT: done, nothing left")
    runner = runner_for(tmp_path, script, session_dir=str(tmp_path / "s"), sandbox=False)
    watch = LimitWatch(1.0, None, 0.8)
    watch.settled = 0.85                         # past the soft share, below the hard limit
    result, _usage, why = runner.work("work on a.txt", working_dir=root, watch=watch, max_calls=5)
    assert why == "" and result.met and watch.softened and watch.end_reason() == "wrapped_up_at_soft_limit"
    assert "next natural safe stopping point" in script.prompts[0]
    assert script.prompts[-1].count("From the hub, not the person") == 1


def test_the_hard_limit_stops_the_loop_and_keeps_its_session_to_resume(tmp_path):
    folder(tmp_path, **{"a.txt": "a"})
    runner = runner_for(tmp_path, Script("RUN: true\nNOTE: n", "REPORT: x"), ceiling_seconds=1e-9, session_dir=str(tmp_path / "s"), sandbox=False)
    got = runner.run_goal(goal="g", brief="b", run_id="r1")
    assert got.cancelled and not got.met and got.end_reason == "stopped_at_hard_limit:time" and "resume" in got.error
    assert (tmp_path / "s" / "r1.json").exists()


def test_a_tree_of_workers_shares_one_set_of_ceilings(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    runner = runner_for(tmp_path, Script("REPORT: one", "REPORT: two"), ceiling_usd=1.0, sandbox=False)
    work = as_solution_worker(runner, root)
    assert work({"task": "t"}) == "one" and work({"task": "t"}) == "two"


def written_figure(tmp_path):
    return folder(tmp_path, **{"facts.txt": "Sales were 12 units.\n"}), edit("out.md", "", "Sales were 99 units.\n") + "REPORT: wrote out.md"


def test_the_review_after_the_code_check_is_put_to_the_stop_decision(tmp_path):
    root, first = written_figure(tmp_path)
    asked = []
    refuse = Script(first)
    got = run_loop("Write out.md with the sales figure from facts.txt.", working_dir=root, complete=refuse, cache_chars=0,
                   permit=lambda kind, facts: (asked.append((kind, facts["rounds"])) or False, "plateau"))
    assert got.met and got.calls == 1 and asked == [("review", [{"findings": 1, "changed": 1}])]      # not reviewed, still met and reported
    assert (tmp_path / "out.md").read_text() == "Sales were 99 units.\n"
    root2 = folder(tmp_path / "b", **{"facts.txt": "Sales were 12 units.\n"})
    allow = Script(first, edit("out.md", "Sales were 99 units.\n", "Sales were 12 units.\n"))
    ok = run_loop("Write out.md with the sales figure from facts.txt.", working_dir=root2, complete=allow, cache_chars=0, permit=lambda kind, facts: (True, "go"))
    assert ok.met and ok.calls == 2


def test_a_repeated_nudge_is_put_to_the_stop_decision_and_a_refusal_ends_not_met_with_the_report(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    script = Script(*["RUN: false\nREPORT: all done"] * 6)
    seen = []

    def permit(kind, facts):
        seen.append((kind, len(facts["rounds"])))
        return False, "plateau"
    got = run_loop("do it", working_dir=root, complete=script, permit=permit, max_calls=6)
    assert not got.met and got.partial and got.ended == "stopped:plateau" and got.report == "all done" and "stopped asking" in got.error
    assert seen == [("nudge", 2)] and got.calls == 2      # the first nudge is ordinary; the second is the hub's own iteration, put to the decision


def test_the_runner_asks_goal_completion_through_the_hub_and_keeps_a_floor_without_it():
    rounds = [{"findings": 3, "spend_usd": 1.0, "elapsed_seconds": 10, "changed": 2}, {"findings": 3, "spend_usd": 2.0, "elapsed_seconds": 20, "changed": 1}]
    facts = dict(rounds=rounds, findings=["x"], ceiling_usd=20.0, ceiling_seconds=14400.0, soft_fraction=0.8)
    plateau = stop_aware(lambda history: STOP)(facts)
    assert plateau["continue"] is False and plateau["reason"] == "plateau" and plateau["decision"] == "stop_not_worth_it"
    assert stop_aware(lambda history: CONTINUE)(facts)["continue"] is True
    history = history_of_rounds(rounds, facts, stated={"one_pass": True})
    assert [i["spend_usd"] for i in history["iterations"]] == [1.0, 1.0] and history["stated"] == {"one_pass": True} and history["ceiling"]["spend_usd"] == 20.0
    # nothing assembled, or nothing to iterate on: the deterministic default decides, as before
    assert stop_aware(lambda history: CONTINUE)(dict(facts, findings=[]))["reason"] == "no_code_finding"
    fallback = stop_aware(None, fallback=lambda f: {"continue": False, "reason": "fallback"})
    original = run_ceilings.selected_stop_decider
    run_ceilings.selected_stop_decider = lambda: None
    try:
        assert fallback(facts)["reason"] == "fallback"
    finally:
        run_ceilings.selected_stop_decider = original
    assert stop_aware()(facts)["decision"] in ("stop_not_worth_it", "stop_good_enough", "continue")      # the selected arm answers (resolved by name)


def test_a_person_who_asked_for_one_pass_is_not_iterated_on(tmp_path):
    facts = dict(rounds=[{"findings": 2, "spend_usd": 0.1, "elapsed_seconds": 5, "changed": 3}], findings=["x", "y"], ceiling_usd=20.0, ceiling_seconds=14400.0)
    decided = stop_aware(stated={"one_pass": True})(facts)
    assert decided["continue"] is False and decided["decision"] == "stop_good_enough" and decided["reason"] == "person_limit"
    assert stop_aware()(facts)["continue"] is True          # nothing stated: one cheap round that changed things earns another


def test_the_stream_runner_wraps_its_run_in_the_ceilings_and_a_hard_stop_names_the_session(tmp_path, monkeypatch):
    seen = {}

    def fake_once(self, **kw):
        watch = run_ceilings.active_watch()
        seen["watch"], seen["control"] = watch, kw["control"]
        watch.hard = "spend"
        from hubofhubs.the_world.tools.deep import DeepResult
        return DeepResult(met=False, session_id="sess-1", cancelled=True)
    monkeypatch.setattr(StreamJsonGoalRunner, "run_goal_once", fake_once)
    runner = StreamJsonGoalRunner(root=str(tmp_path), ceiling_usd=5.0)
    got = runner.run_goal(goal="g", brief="b")
    assert seen["watch"].ceiling_usd == 5.0 and seen["control"] is not None and run_ceilings.active_watch() is None
    assert got.end_reason == "stopped_at_hard_limit:spend" and "sess-1" in got.error and got.resume_handle == "sess-1"
    free = StreamJsonGoalRunner(root=str(tmp_path), ceiling_usd=UNLIMITED, ceiling_seconds=UNLIMITED)
    seen.clear()
    free.run_goal(goal="g", brief="b")
    assert seen["watch"] is None and seen["control"] is None      # no ceiling at all: the session runs as it always did


def test_the_spend_estimate_counts_each_message_once_and_prices_the_cache(tmp_path, monkeypatch):
    import json
    import importlib
    headless_runner = importlib.import_module("hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner")   # the module the estimate itself imports, whatever another test did to the package attribute
    monkeypatch.setattr(headless_runner, "list_price", lambda provider, model, tin, tout: tin * 1e-6 + tout * 1e-5)    # a flat table: the shape of the sum is what is checked
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 300, "cache_read_input_tokens": 1000, "output_tokens": 5,
             "cache_creation": {"ephemeral_1h_input_tokens": 200, "ephemeral_5m_input_tokens": 100}}
    final = dict(usage, output_tokens=50)       # a message split in two blocks repeats its input counts; the last block holds the final output
    lines = [{"type": "assistant", "message": {"id": "m1", "model": "x", "usage": usage}},
             {"type": "assistant", "message": {"id": "m1", "model": "x", "usage": final}},
             {"type": "user", "message": {"content": "no usage"}}]
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
    expected = (10 + 2.0 * 200 + 1.25 * 100 + 0.1 * 1000) * 1e-6 + 50 * 1e-5
    assert run_ceilings.estimate_spend(str(path)) == pytest.approx(expected)
    assert run_ceilings.estimate_spend(str(tmp_path / "missing.jsonl")) == 0.0 and run_ceilings.estimate_spend(None) == 0.0


def test_a_hard_stop_names_the_hard_limit_whatever_the_runner_said_about_the_stop():
    from types import SimpleNamespace
    watch = LimitWatch(None, 1.0)
    watch.hard = "time"
    result = SimpleNamespace(cancelled=True, paused=False, error="The run was stopped on request.", session_id="s1", cost_usd=0.0)
    watch.finish(result)
    assert "hard limit (time)" in result.error and "resume session s1" in result.error and result.end_reason == "stopped_at_hard_limit:time"
    paused = SimpleNamespace(cancelled=True, paused=True, error="paused by the person", session_id="s2", cost_usd=0.0)
    watch.finish(paused)
    assert paused.error == "paused by the person"


def test_the_text_loop_reports_its_run_like_the_other_runners(tmp_path):
    root = folder(tmp_path, **{"a.txt": "a"})
    runner = runner_for(tmp_path, Script("REPORT: done, nothing left"), session_dir=str(tmp_path / "s"), sandbox=False)
    result = runner.run_goal(goal="look at a.txt", working_dir=root, run_id="r1")
    assert result.resume_handle == result.session_id == "r1" and result.spend_usd == result.cost_usd and result.elapsed_seconds >= 0.0
