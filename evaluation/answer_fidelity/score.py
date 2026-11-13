"""Scores an answer check: given a final answer and a reference, does the check flag an answer that does not do what the person's own words asked, and leave a good one alone?

Each case (``build_cases.py``) is the person's first message verbatim, the answer a session ended with, the agent's own restatement of the goal, and whether the answer should pass. An arm
(``impls/``) returns the check's verdict for the case, reading either the original input or the paraphrase. The four kinds: ``drift`` and ``partial`` must be flagged, ``correct`` and
``honest_none`` (an answer that says plainly, with what it looked at, that it found nothing about the named subject, and gives its own view) must pass.

Fixed before any arm was scored (this file is the record; a change to any line below is a new version of the metric, not a tuning):

  * ``detection`` = the share of the cases that must be flagged (drift and partial) that the check flagged.
  * ``false_alarm`` = the share of the cases that must pass (correct and honest_none) that the check flagged.
  * Score = the mean of ``detection`` and ``1 - false_alarm``, so an arm that never flags (no check) scores 0.5 and an arm that always flags scores 0.5; only telling the two groups apart
    scores higher. A flag costs a resumed turn, a missed drift costs the person's trust, and the owner named the missed drift, so neither is weighed above the other.
  * A verdict that cannot be read is no opinion and counts as no flag (the run keeps its answer), as it does in a real run.
  * The paraphrase arm models the failure that raised this stage: a check that reads the agent's own restated goal inherits the drift. Its paraphrases are written by the case builder
    (the goal as the answer had narrowed or moved it for drift and partial; a faithful short restatement for the other kinds), so its score shows the cost of the reference and is not a
    claim about every restatement.
What it cannot see: answers longer or subtler than these (a few sentences each), subjects that are ambiguous, and how often a real session drifts."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MUST_FLAG = ("drift", "partial")
MUST_PASS = ("correct", "honest_none")


def flagged_by(verdict: Any) -> bool:
    return isinstance(verdict, dict) and verdict.get("passed") is False


def score_case(fn, case):
    verdict = fn(case["kind"], case["args"])
    flagged = flagged_by(verdict)
    ok = flagged is (not case["expect"])
    note = "" if ok else ("missed: the check let it pass" if flagged is False and not case["expect"] else "false alarm: the check flagged a good answer")
    if verdict is None:
        note = (note + "; " if note else "") + "no readable verdict"
    return dict(ok=ok, flagged=flagged, kind=case["kind"], note=note, got="flagged" if flagged else "passed")


def share(rows: List[Dict[str, Any]], key: str = "ok") -> str:
    return f"{sum(bool(r[key]) for r in rows)}/{len(rows)}"


def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    bad = [r for r in rows if r.get("kind") in MUST_FLAG]
    good = [r for r in rows if r.get("kind") in MUST_PASS]
    detection = sum(bool(r["flagged"]) for r in bad) / max(len(bad), 1)
    false_alarm = sum(bool(r["flagged"]) for r in good) / max(len(good), 1)
    out: Dict[str, Any] = {"detection": f"{detection:.3f}", "false_alarm": f"{false_alarm:.3f}", "fidelity": f"{(detection + 1 - false_alarm) / 2:.3f}"}
    for kind in MUST_FLAG + MUST_PASS:
        mine = [r for r in rows if r.get("kind") == kind]
        out[f"{kind}_ok"] = share(mine)
    out["unreadable"] = sum("no readable verdict" in str(r.get("note")) for r in rows)
    return out
