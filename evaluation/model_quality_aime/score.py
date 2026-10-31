"""Scores a model on AIME 2025 I and II (30 problems, integer answers 0 to 999) with one prompt for every model.

Pass = the integer after the last ``Final answer:`` (else the last ``\\boxed{}``) equals the gold answer exactly. The problem text is loaded from a pinned mirror
(``problems.py``); arms are in ``impls/``. Cost is the metered tokens (thinking included) times the price in
``hubofhubs/registry/tier_prices.csv``; Claude arms run on a subscription and are counted in calls.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model_quality_aime.problems import load_cases  # noqa: E402,F401  (the harness reads cases from here)


def final_integer(text):
    """The integer after the last ``Final answer:`` (markdown bold or ``$`` tolerated), or None."""
    found = re.findall(r"final answer:?\**\s*\$?\s*\**\s*(\d+)\b(?!\.\d)", text or "", flags=re.IGNORECASE)
    if not found:   # the model gave its answer in the usual maths form instead of the asked line: the last \boxed{<integer>} counts
        found = re.findall(r"\\boxed\{\s*(\d+)\s*\}", text or "")
    return int(found[-1]) if found else None


def score_case(fn, case):
    text = fn(case["kind"], {"question": case["question"]})
    got, want = final_integer(text), int(case["expect"])
    ok = got is not None and got == want
    return dict(ok=ok, got="none" if got is None else str(got), note="" if ok else f"expected {want}")
