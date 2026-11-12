"""The balanced number of Delegated Agent Sessions lets pass count dominate: one more passed case outweighs everything cost and time can add."""
import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
COMPONENTS = ("agent_sessions", "agent_sessions_hard", "agent_sessions_depth")


def table(component):
    with (ROOT / "esoi.toml").open("rb") as handle:
        return tomllib.load(handle)["balance"][component]


def case_count(component):
    return len(json.loads((ROOT / "evaluation" / component / "cases.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("component", COMPONENTS)
def test_one_more_passed_case_outweighs_all_cost_and_time(component):
    weights = table(component)["weights"]
    cases = case_count(component)
    one_case = weights["accuracy"] / cases
    most_cost_and_time_can_add = weights["cost"] + weights["time"]
    assert one_case > most_cost_and_time_can_add, (
        f"{component}: a case is worth {one_case:.4f} but cost and time can add up to {most_cost_and_time_can_add:.4f}; "
        f"accuracy must exceed {cases / (cases + 1):.4f}")


@pytest.mark.parametrize("component", COMPONENTS)
def test_the_weights_sum_to_one_and_cost_and_time_are_equal(component):
    weights = table(component)["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights["cost"] == weights["time"]


def test_both_sets_use_the_same_weights():
    assert table("agent_sessions")["weights"] == table("agent_sessions_hard")["weights"] == table("agent_sessions_depth")["weights"]


def test_a_six_of_nine_arm_never_outranks_an_eight_of_nine_arm():
    from esoi.optimization.measurement_harness.balance import balanced
    cfg = table("agent_sessions_hard")
    cheapest = balanced(6, 9, 0.0, 0.0, cfg)["balanced"]
    dearest_in_budget = balanced(8, 9, 9 * cfg["cost_per_case_usd"], 9 * cfg["seconds_per_case"], cfg)["balanced"]
    assert cheapest < dearest_in_budget
