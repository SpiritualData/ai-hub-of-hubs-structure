"""The esoi library's lexical_index arm of Solution Relevance over this hub's own records, parents included. Zero model calls."""
from pathlib import Path

from esoi.understanding.solution_relevance import relevance_cases

ROOT = Path(__file__).resolve().parents[3]


def build(meter):
    return relevance_cases.runner(ROOT, "lexical_index")
