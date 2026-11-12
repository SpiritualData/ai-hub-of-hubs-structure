"""The file_edit_goals arm: the Claude CLI provider, the model the tier chooser names for the tier, and the tier carried by the arm name. Offline, no model call."""
import datetime
import importlib
import sys
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
score = importlib.import_module("file_edit_goals.score")
arm = importlib.import_module("file_edit_goals.impls.fast_edit")
from esoi import RunError  # noqa: E402
from esoi.optimization.measurement_harness.call_meter import CallMeter  # noqa: E402


def test_the_tier_is_the_arm_names_else_the_variable_else_fast():
    assert score.tier_of(None, {}) == "fast" and score.tier_of(None, {"FILE_EDIT_TIER": "fast"}) == "fast"
    assert score.tier_of("balanced", {}) == "balanced" and score.tier_of("quality", {"FILE_EDIT_TIER": "balanced"}) == "quality"


def test_a_tier_that_the_arm_name_does_not_carry_is_refused_so_the_record_cannot_mislabel_it():
    with pytest.raises(RunError, match="arm name"):
        score.tier_of(None, {"FILE_EDIT_TIER": "balanced"})
    for bad in ("best", "gemini"):
        with pytest.raises(RunError):
            score.tier_of(bad, {})
    with pytest.raises(RunError):
        score.tier_of("fast", {})      # fast is the arm with no parameter, the spelling the role tier table matches


@pytest.mark.parametrize("tier", score.TIERS)
def test_the_meter_model_is_the_model_the_chooser_names_today(tier):
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import tiers
    meter = CallMeter()
    provider, model = score.claude_provider(meter, tier)
    assert meter.model == model == tiers.choose(today=datetime.date.today().isoformat())[tier]["arm"][1]
    assert type(provider).__name__ == "ClaudeCliProvider" or hasattr(provider, "answer")


def test_the_eval_names_no_model_and_no_gemini():
    text = "".join(p.read_text(encoding="utf-8") for p in (EVALUATION / "file_edit_goals").glob("**/*.py") if "__pycache__" not in str(p)).lower()
    assert "gemini" not in text and "haiku" not in text


def test_the_arm_edits_through_the_runner_and_the_case_checks_it(monkeypatch):
    class Provider:
        def answer(self, messages, *, model, system=None, layers=None):
            return "solution.py\n```\ndef add(a, b):\n    return a + b\n```\n"
    monkeypatch.setattr(arm, "claude_provider", lambda meter, tier: (Provider(), "m-now"))
    case = dict(stub="def add(a, b):\n    pass\n", test="def check(candidate):\n    assert candidate(1, 2) == 3\n", entry_point="add", solution="def add(a, b):\n    return a + b\n")
    got = score.score_case(arm.build(CallMeter()), case)
    assert got["ok"] and got["got"].startswith("edited")
