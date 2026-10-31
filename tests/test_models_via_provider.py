"""Offline test of the model-call arm built on the call-a-model seat: a recording provider, no model, no network."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs  # noqa: E402
from hubofhubs.models.via_provider import ViaCallAModel  # noqa: E402


class Provider:
    def __init__(self):
        self.calls = []

    def answer(self, messages, *, model, system=None, layers=None):
        self.calls.append((messages, model, system))
        return "reply"


def test_a_tier_maps_to_a_model_and_an_unlisted_tier_is_the_model_id():
    provider = Provider()
    arm = ViaCallAModel(provider, tiers={"fast": "m-fast"}, system="Be brief.")
    assert arm.complete("hi", "fast") == "reply" and arm.complete("hi", "other-model") == "reply"
    assert [(c[1], c[2]) for c in provider.calls] == [("m-fast", "Be brief."), ("other-model", "Be brief.")]
    assert provider.calls[0][0] == [{"role": "user", "content": "hi"}]


def test_an_empty_tier_uses_the_default_or_refuses():
    assert ViaCallAModel(Provider(), default_tier="x").complete("q") == "reply"
    with pytest.raises(ValueError, match="default_tier"):
        ViaCallAModel(Provider()).complete("q")


def test_the_hub_builds_it_over_the_call_a_model_seat():
    system = hubofhubs.assemble(arms={"call-a-model": "gemini", "model-call": "via_call_a_model"}, options={"model-call": {"default_tier": "m"}},
                                environ={"GOOGLE_API_KEY": "not-a-real-key"})
    assert isinstance(system["model-call"], ViaCallAModel) and system["model-call"].provider is system["call-a-model"]
    assert "not-a-real-key" not in " ".join(system.reasons) and "api_key <- GOOGLE_API_KEY" in " ".join(system.reasons)
    pending = hubofhubs.assemble(arms={"call-a-model": "gemini", "model-call": "via_call_a_model"}).pending
    assert "GOOGLE_API_KEY" in pending["call-a-model"] and pending["model-call"].endswith("needs call-a-model; see those lines")
