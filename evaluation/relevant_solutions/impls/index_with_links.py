"""The esoi library's index_with_links arm of Solution Relevance over this hub's own records, parents included. Zero model calls."""
from pathlib import Path

ALTERNATIVE = True   # the esoi library's own arm over the hub's records, the baseline the hub's records_index arm is compared with

from esoi.understanding.solution_relevance import relevance_cases

ROOT = Path(__file__).resolve().parents[3]


def build(meter):
    return relevance_cases.runner(ROOT, "index_with_links")
