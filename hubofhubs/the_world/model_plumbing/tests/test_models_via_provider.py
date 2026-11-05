"""Offline test of the model-plumbing arm built on the vendor-model-caller seat: a recording provider, no model, no network."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import hubofhubs  # noqa: E402
from hubofhubs.the_world.model_plumbing.via_vendor import BudgetSpent, ViaVendor  # noqa: E402


class NoChooser:
    def choose(self):
        return {}


class Provider:
    def __init__(self):
        self.calls = []

    def answer(self, messages, *, model, system=None, layers=None):
        self.calls.append((messages, model, system))
        return "reply"


def test_a_tier_maps_to_a_model_and_an_unlisted_tier_is_the_model_id():
    provider = Provider()
    arm = ViaVendor(provider, NoChooser(), tiers={"fast": "m-fast"}, system="Be brief.")
    assert arm.ask("hi", "fast") == "reply" and arm.ask("hi", "other-model") == "reply"
    assert [(c[1], c[2]) for c in provider.calls] == [("m-fast", "Be brief."), ("other-model", "Be brief.")]
    assert provider.calls[0][0] == [{"role": "user", "content": "hi"}]


def test_an_empty_tier_uses_the_default_or_refuses():
    assert ViaVendor(Provider(), NoChooser(), default_tier="x").ask("q") == "reply"
    with pytest.raises(ValueError, match="default_tier"):
        ViaVendor(Provider(), NoChooser()).ask("q")


def test_the_budget_of_the_goal_record_is_spent_one_call_at_a_time():
    provider, budget = Provider(), {"model_calls": 1}
    arm = ViaVendor(provider, NoChooser(), default_tier="m")
    assert arm.ask("hi", budget=budget) == "reply" and budget["model_calls"] == 0
    with pytest.raises(BudgetSpent):
        arm.ask("hi", budget=budget)
    assert len(provider.calls) == 1


def test_the_hub_builds_it_over_the_vendor_model_caller_seat():
    system = hubofhubs.assemble(arms={"vendor-model-caller": "gemini"}, options={"model-plumbing": {"default_tier": "m"}},
                                environ={"GOOGLE_API_KEY": "not-a-real-key"})
    assert isinstance(system["model-plumbing"], ViaVendor) and system["model-plumbing"].vendor is system["vendor-model-caller"]
    assert "not-a-real-key" not in " ".join(system.reasons) and "api_key <- GOOGLE_API_KEY" in " ".join(system.reasons)
    pending = hubofhubs.assemble(arms={"vendor-model-caller": "gemini"}, environ={}).pending
    assert "GOOGLE_API_KEY" in pending["vendor-model-caller"] and pending["model-plumbing"].endswith("needs vendor-model-caller; see those lines")
