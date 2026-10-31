"""The AIME component's answer reading, case file and baseline: offline, no model call, no network."""
import importlib
import json
import sys
from pathlib import Path

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
score = importlib.import_module("model_quality_aime.score")
CASES = json.loads((EVALUATION / "model_quality_aime" / "cases.json").read_text())


def test_the_final_line_is_read_and_a_boxed_answer_is_the_fallback():
    assert score.final_integer("work\nFinal answer: 588") == 588
    assert score.final_integer("**Final answer: 70**") == 70
    assert score.final_integer("Final answer: 5\nFinal answer: 117") == 117, "the last line counts"
    assert score.final_integer("so $\\boxed{117}$") == 117
    for text in ("", "I am not sure.", "Final answer: 3.5", "Final answer: forty", "\\boxed{1/2}"):
        assert score.final_integer(text) is None, text


def test_the_thirty_cases_are_ids_and_integer_answers_without_the_problem_text():
    assert len(CASES) == 30 and len({c["id"] for c in CASES}) == 30
    for case in CASES:
        assert 0 <= int(case["expect"]) <= 999 and len(case["text_sha256"]) == 64
        assert "question" not in case, "the MAA's problem text is fetched, never committed"


def test_the_baseline_that_never_answers_fails_every_case():
    build = importlib.import_module("model_quality_aime.broken.no_answer").build
    fn = build(None)
    assert not any(score.score_case(fn, dict(case, question="q"))["ok"] for case in CASES)


def test_the_pinned_source_files_are_named_with_a_sha256():
    problems = importlib.import_module("model_quality_aime.problems")
    assert set(problems.FILES) == {"aime2025-I.jsonl", "aime2025-II.jsonl"}
    assert all(len(v) == 64 for v in problems.FILES.values()) and len(problems.COMMIT) == 40
    assert {c["source"].split(":")[0] for c in CASES} == set(problems.FILES)
