"""The context-assembler component's scoring helpers: nDCG@10, recall@10, rank extraction and the fixed case file. No network."""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation" / "context_assembler"))
import score  # noqa: E402


def test_ndcg_uses_grade_as_gain_and_log2_discount():
    relevant = {"a": 2, "b": 1}
    assert score.ndcg_at(["a", "b"], relevant) == 1.0
    worse = score.ndcg_at(["x", "b", "a"], relevant)
    ideal = 2 / math.log2(2) + 1 / math.log2(3)
    assert abs(worse - (1 / math.log2(3) + 2 / math.log2(4)) / ideal) < 1e-12
    assert score.ndcg_at(["x"], relevant) == 0.0


def test_recall_counts_relevant_found_in_top_ten():
    assert score.recall_at(["a", "x", "b"], {"a": 1, "b": 1, "c": 1}) == 2 / 3
    assert score.recall_at(["x"] * 10 + ["a"], {"a": 1}) == 0.0


def test_vector_rank_comes_from_effective_score_and_the_bm25_suffix_is_removed():
    vector = SimpleNamespace(card_ids=["a", "b"], card_metadata=[dict(id="a", effective_score=0.1), dict(id="b", effective_score=0.9)])
    assert score.ranked_ids("VectorContextAssembler", vector) == ["b", "a"]
    bm25 = SimpleNamespace(card_ids=["x.txt", "y.txt", "x.txt"], card_metadata=[])
    assert score.ranked_ids("BM25ContentStore", bm25) == ["x", "y"]


def test_a_case_passes_on_a_relevant_document_in_the_top_five_only():
    case = dict(id="q", relevant={"d": 1})
    assert score.score_case(lambda q: ["a", "b", "c", "e", "d"], case)["ok"]
    assert not score.score_case(lambda q: ["a", "b", "c", "e", "f", "d"], case)["ok"]


def test_case_file_holds_ids_and_grades_only():
    cases = score.load_cases()
    assert len(cases) == 323
    assert all(set(c) == {"id", "relevant"} and set(c["relevant"].values()) <= {1, 2} for c in cases)
    assert "nutritionfacts" not in json.dumps(cases).lower()
