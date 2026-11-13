"""Scores a Terminal Experience arm on what a person who used it on a real terminal said: the human trial stage of metric-terminal-presentation (revision 6, 2026-11-12).

The evidence is a ledger, ``human_verdicts.csv``, append-only: one row per verdict with who said it, when, which arm, which aspect, whether it is a ``strength`` or a ``limit``, the reason in the
person's own words and the source. A later verdict about the same arm and aspect replaces the earlier one in the reading (the earlier row stays in the file). Nothing here is edited when a
person tries another arm or changes their mind: a verdict is appended, ``build_cases.py`` is run (it makes one case per aspect the ledger names) and the arms are re-recorded (free, instant).

One case is one aspect. For an arm the case passes unless the arm's latest verdict on that aspect is a limit (a person who said nothing about it has recorded no limit), and its graded score is
1 where the latest verdict is a strength and 0 otherwise (a strength is the evidence of a quality, so an arm nobody commented on has not shown it). The pass rate is therefore the share of
aspects with no recorded limit, and the balanced score is the share of aspects with a recorded strength, balanced with cost and time by ``[balance.terminal_trial]``. The cascade of
metric-terminal-presentation reads this component as a requirement of its stage (``requires=terminal_trial:1:1``): an arm with a recorded limit is not selectable until a later verdict replaces
it. Nobody's preference sets ``selected``; the strengths are on record beside the screen probes, which measure the same things (a palette, tabs, going into helpers, a marker per kind of update)
where a screen can show them.

The arm is named by the snake case of its class (``LiveSession`` is ``live_session``), the implementation id the records use. Standard library only."""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "human_verdicts.csv"
COLUMNS = ("verdict_id", "date", "who", "arm", "aspect", "verdict", "reason", "source")
VERDICTS = ("strength", "limit")


def arm_id(implementation):
    """The implementation id of an arm: the snake case of its class name."""
    name = getattr(implementation, "__name__", None) or type(implementation).__name__
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def ledger_rows():
    with LEDGER.open(newline="") as handle:
        return list(csv.DictReader(handle))


def latest(arm, aspect, rows=None):
    """The arm's latest verdict row on the aspect (a later date wins; on the same date, the later row), or None when nobody said anything."""
    mine = [r for r in (rows if rows is not None else ledger_rows()) if r["arm"] == arm and r["aspect"] == aspect]
    return sorted(mine, key=lambda r: r["date"])[-1] if mine else None


def adapt(implementation, meter):
    arm = arm_id(implementation)

    def run(kind, args):
        row = latest(arm, args["aspect"])
        return {"verdict": row["verdict"] if row else "", "who": row["who"] if row else "", "date": row["date"] if row else "", "reason": row["reason"] if row else ""}
    return run


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    limit, strength = got["verdict"] == "limit", got["verdict"] == "strength"
    said = f"{got['who']} on {got['date']}: {got['reason']}" if got["verdict"] else "nothing said"
    return dict(ok=not limit, score=1.0 if strength else 0.0, got=got["verdict"] or "nothing said", note=(f"a limit was recorded ({said})" if limit else ""), kind=case["kind"], requirements=[])
