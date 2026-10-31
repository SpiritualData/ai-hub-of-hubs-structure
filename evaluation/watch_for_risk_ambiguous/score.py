"""Scores a watch-for-risk arm on ambiguous steps: the same check, prompt, model and signal rule as ``watch_for_risk``, on 24 other cases.

A new case file is a new stage, so this is its own component and its rows are compared only with each other (their own ``cases_sha``).
The arms are the seat's own: ``overseer`` (model), ``none``, ``consent_gate`` (rules) and ``two_stage`` (rules, then the model when unsure).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from watch_for_risk.score import MODEL, PROMPT, adapt, make_provider, render, score_case  # noqa: E402,F401
