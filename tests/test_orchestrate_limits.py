"""The loop defaults are pinned, and the two result predicates read structure only."""
from types import SimpleNamespace as NS

from hubofhubs.orchestrate import limits
from hubofhubs.orchestrate.limits import result_landed_work, result_reports_something


def test_the_defaults_are_pinned():
    assert (limits.DEFAULT_MAX_STEPS, limits.DEFAULT_MAX_ELAPSED_SECONDS, limits.DEFAULT_MAX_GATHERED_CHARS) == (15, 90.0, 150000)
    assert (limits.DEFAULT_MAX_PLAN_STAGES, limits.DEFAULT_MAX_PLAN_TASKS, limits.DEFAULT_MAX_DEEP_SUBTASKS) == (4, 8, 4)
    assert limits.AUTO_FOLLOWUP_TOKEN_BUDGET == 300_000 * (1 + limits.AUTO_FOLLOWUP_MAX_RUNS)
    assert limits.DEFAULT_CARD_MERGE_SIMILARITY == 0.85 and limits.DEFAULT_PLANNER_ABBREVIATE_REPEAT_CONTEXT is True


def test_a_result_reports_something_when_it_has_text_a_verified_outcome_or_a_wait():
    assert result_reports_something(NS(output=" text ")) and result_reports_something(NS(output="", met=True))
    assert result_reports_something(NS(output="", usage_limited=True))
    assert not result_reports_something(NS(output="  "))
    assert not result_reports_something(object())


def test_parked_or_unchanged_work_did_not_land():
    assert not result_landed_work(NS(decision_id="d1")) and not result_landed_work(NS(changed_nothing=True))


def test_a_runner_without_receipts_is_judged_landed():
    assert result_landed_work(NS(output="answer"))


def test_a_receipt_tracking_run_that_observed_nothing_and_was_not_met_did_not_land():
    assert not result_landed_work(NS(observations_reported=True, met=False, observations=[]))


def test_an_exhausted_terminal_ask_did_not_land_unless_a_partial_write_did():
    ask = NS(observations_reported=True, met=False, observations=["read"], exhausted=True, has_write_receipt=False)
    assert not result_landed_work(ask)
    ask.has_write_receipt = True
    assert result_landed_work(ask)
    assert result_landed_work(NS(observations_reported=True, met=True, observations=[], exhausted=True))
