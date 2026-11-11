"""The depth cases of Delegated Agent Sessions: the naive baseline fails every one, a hand-written correct result passes every one, the case file
is what its builder writes, and the case data reaches only an arm whose constructor takes it. Free: no model call."""
import functools
import importlib
import json
import sys
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
FOLDER = EVALUATION / "agent_sessions_depth"


def module(name):
    return importlib.import_module(f"agent_sessions_depth.{name}")


def cases():
    return json.loads((FOLDER / "cases.json").read_text(encoding="utf-8"))


def test_cases_json_is_what_the_builder_writes():
    built = module("build_cases").cases()
    assert json.loads(json.dumps(built)) == cases()


def test_every_case_has_a_goal_and_a_code_check():
    for case in cases():
        assert case["goal"] and case["stratum"]
        assert case.get("expect_report") or case.get("expect_json") or case.get("hidden_tests"), case["id"]


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_the_parrot_baseline_fails_the_case(case):
    parrot = module("broken.parrot").build(None)
    assert not module("score").score_case(parrot, case)["ok"]


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_a_hand_written_correct_result_passes_the_case(case):
    reference = module("reference").build(None)
    row = module("score").score_case(reference, case)
    assert row["ok"], row["note"]


def test_a_correct_result_that_touches_a_fixed_file_fails():
    case = next(c for c in cases() if c["id"] == "depth-solution-records")
    reference = module("reference").build(None)

    def meddling(kind, args):
        (Path(args["root"]) / "report/rounding.py").write_text("def round_half_even(value):\n    return value\n", encoding="utf-8")
        return reference(kind, args)

    row = module("score").score_case(meddling, case)
    assert not row["ok"] and "files changed" in row["note"]


def test_a_wrong_claim_repeated_fails_the_recall_case():
    case = next(c for c in cases() if c["id"] == "depth-recall-known")
    reference = module("reference").build(None)

    def believer(kind, args):
        result = reference(kind, args)
        (Path(args["root"]) / "answer.json").write_text(json.dumps({"retry_limit": 9, "source_file": "config/settings.ini"}), encoding="utf-8")
        return result

    assert not module("score").score_case(believer, case)["ok"]


def test_the_skills_folder_and_the_known_text_reach_only_an_arm_that_takes_them():
    score = module("score")

    class Takes:
        def __init__(self, config=None, *, settings=None, skills_dir=None, recall=None, **ignored):
            pass

    class Refuses:
        def __init__(self, config=None, *, settings=None, **ignored):
            pass

    args = {"skills_dir": "/somewhere", "known": "a finding"}
    taken = score.extras_for(Takes, args)
    assert taken["skills_dir"] == "/somewhere" and taken["recall"]("any goal") == "a finding"
    assert set(score.extras_for(functools.partial(Takes, provider="x"), args)) == {"skills_dir", "recall"}
    assert score.extras_for(Refuses, args) == {}
    assert score.extras_for(Takes, {"goal": "g"}) == {}


def test_the_skills_case_hands_the_skills_folder_to_the_arm_and_leaves_the_work_folder_without_the_rule():
    case = next(c for c in cases() if c["id"] == "depth-skills-folder")
    assert not any("shipping" in text.lower() and "75.00" in text for text in case["files"].values())
    seen = {}

    def spy(kind, args):
        seen.update(args)
        return module("reference").build(None)(kind, args)

    module("score").score_case(spy, case)
    assert "skills_dir" in seen and "known" not in seen
