"""Scores a know-the-world arm on the 150-question stage: same matching rule, arms and cost counting as ``know_the_world``, more cases.

The first 40 cases are the cases of ``know_the_world``; a different case file is a different stage, so these rows are compared only with each
other (their own ``cases_sha``).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from know_the_world.score import adapt, score_case  # noqa: E402,F401
