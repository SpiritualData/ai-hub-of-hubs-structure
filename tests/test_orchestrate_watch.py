"""The overseer wake-up gate fires on a stuck read loop, a repeated plan or budget pressure, and fails closed."""
from hubofhubs.orchestrate.watch import worth_a_look

CALM = dict(consecutive_reads=1, plan_repeats_prev=False, elapsed_seconds=10.0, max_elapsed_seconds=90.0,
            gathered_chars=1000, max_gathered_chars=150000, min_consecutive_reads=5, gate_repeat_plan=True,
            spend_fraction=0.5)


def test_a_calm_step_is_not_worth_a_look():
    assert worth_a_look(**CALM) is False


def test_each_signal_wakes_the_gate():
    assert worth_a_look(**{**CALM, "consecutive_reads": 5})
    assert worth_a_look(**{**CALM, "plan_repeats_prev": True})
    assert not worth_a_look(**{**CALM, "plan_repeats_prev": True, "gate_repeat_plan": False})
    assert worth_a_look(**{**CALM, "elapsed_seconds": 45.0})
    assert worth_a_look(**{**CALM, "gathered_chars": 75000})


def test_zero_budgets_and_bad_input_are_quiet():
    assert not worth_a_look(**{**CALM, "max_elapsed_seconds": 0, "max_gathered_chars": 0})
    assert worth_a_look(**{**CALM, "consecutive_reads": 0, "min_consecutive_reads": 0}) is False
    assert worth_a_look(**{**CALM, "min_consecutive_reads": "x"}) is False
