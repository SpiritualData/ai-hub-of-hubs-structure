"""The hard cases of Delegated Agent Sessions fail the naive baseline: an agent that parrots the goal back passes none of them, and no
judge is asked. The case bodies are private, so the test runs only where the folders that hold them are named."""
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
CASES = json.loads((EVALUATION / "agent_sessions_hard" / "cases.json").read_text())
PRIVATE = "AGENT_SESSIONS_HARD_CASES"


def test_the_baseline_module_is_the_naive_agent():
    parrot = importlib.import_module("agent_sessions_hard.broken.parrot").build(None)
    reply = parrot("goal", {"goal": "do the thing"})
    assert reply.output == "do the thing" and reply.met and reply.cost_usd == 0.0


@pytest.mark.skipif(not os.environ.get(PRIVATE), reason="the hard cases' bodies are private; name their folders to run this")
def test_the_parrot_baseline_fails_every_hard_case_without_a_judge(monkeypatch):
    score = importlib.import_module("agent_sessions_hard.score")

    def no_judge(prompt):
        raise AssertionError("the judge is not asked about an agent that wrote nothing")

    monkeypatch.setattr(score, "ask_judge", no_judge)
    parrot = importlib.import_module("agent_sessions_hard.broken.parrot").build(None)
    cases = CASES["cases"] if isinstance(CASES, dict) else CASES
    assert cases and not any(score.score_case(parrot, case)["ok"] for case in cases)
