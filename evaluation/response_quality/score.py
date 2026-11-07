"""Scores a Response Quality arm: does it report exactly the findings the rule of the case gives, and nothing for the rules it does not judge?

The cases are invented, neutral responses with the evidence text they are held to (``build_cases.py`` names the rule of each family). Every arm runs on every case; the
case's ``expect`` names the findings of each arm and an arm it does not name must report none. One number: the share of cases whose findings equal the written ones, balanced
with cost and time by ``[balance.response_quality]`` (accuracy 70%, cost 15%, time 15%, fixed before any arm was scored). No model call, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

ARM_KEYS = {"EvidenceCheck": "evidence_check", "GroundedFigures": "grounded_figures", "EmDashFree": "em_dash_free", "DateArithmetic": "date_arithmetic"}


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        return list(arm.judge(args["response"], args["evidence"]))
    run.arm = ARM_KEYS.get(implementation.__name__, implementation.__name__)
    return run


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    return dict(judge(got, {"expect": case["expect"].get(fn.arm, [])}), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in sorted({r.get("kind") for r in rows})}
