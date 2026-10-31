"""Each offline component's cases tell the real arm from the naive baseline in its broken/ folder: the baseline fails at least one case."""
import importlib
import json
import sys
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
COMPONENTS = ["card_store", "stay_current", "connect_any_integration", "reason_and_answer", "model_call", "assemble_the_whole",
              "provider_failover", "watch_for_risk", "watch_for_risk_ambiguous", "call_a_model"]


def failures(component, build):
    score = importlib.import_module(f"{component}.score")
    cases = json.loads((EVALUATION / component / "cases.json").read_text())
    fn = build(None)
    failed = 0
    for case in cases:
        try:
            failed += not score.score_case(fn, case)["ok"]
        except Exception:
            failed += 1
    return failed, len(cases)


@pytest.mark.parametrize("component", COMPONENTS)
def test_every_baseline_fails_some_case(component):
    baselines = sorted(p.stem for p in (EVALUATION / component / "broken").glob("*.py") if p.name != "__init__.py")
    assert baselines
    for name in baselines:
        build = importlib.import_module(f"{component}.broken.{name}").build
        failed, total = failures(component, build)
        assert 0 < failed <= total, f"{component}/{name} fails {failed} of {total}"


@pytest.mark.parametrize("component", COMPONENTS)
def test_the_component_has_enough_cases_and_unique_ids(component):
    cases = json.loads((EVALUATION / component / "cases.json").read_text())
    assert len(cases) >= (20 if component == "watch_for_risk_ambiguous" else 30) and len({c["id"] for c in cases}) == len(cases)
