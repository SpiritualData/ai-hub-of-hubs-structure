"""BASELINE: no lookup. It returns the question back as its observation, as a lazy first draft would. Zero calls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from hubofhubs.ports.retrieval import Observation  # noqa: E402


def build(meter):
    return lambda kind, args: Observation(kind="query", text=f'SCHOLARLY WORKS for "{args["question"]}": {args["question"]}')
