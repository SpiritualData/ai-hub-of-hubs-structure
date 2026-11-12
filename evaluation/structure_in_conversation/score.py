"""Scores a Structure in Conversation arm on structured fields, never prose: given the move a turn calls for and the records the system holds, does the reply carry
the structure the move calls for (the parts, each from the records first and the draft for what is missing), make no move where the turn must stay plain, reuse
an existing solution, alternative and metric instead of adding a duplicate, state a metric value only when the records hold it, make at most one offer that adds
only the missing pieces, and stay quiet about an offer that was declined or a milestone of a held solution? One number: the share of cases whose projected result
equals what the case expects; every case counts once, so the share by kind shows where an arm is weak. Written cases; no model call.

The advisory judged checks (consistent terms, stands alone for a newcomer) are in ``hubofhubs/the_intelligence/critical_thinking/structure_in_conversation/advisory.py``
and are never part of this number."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

KINDS = ("stay_out", "frame_bare", "frame_existing", "reuse_complete", "compare", "review", "focus", "declined", "held", "several")


def part_state(part):
    return None if not part else ("existing" if part.get("existing") else "proposed")


def project(result):
    """The fields of a result that are scored: the move, the parts present, whether each of solution, metric and milestone is held or proposed, how many alternatives
    are held and new, the metric value shown, and the offer's pieces and number of edits."""
    block, offer = result.get("block"), result.get("offer")
    block = block or {}
    alternatives = block.get("alternatives") or []
    metric = block.get("metric") or {}
    return {"move": result.get("move"), "parts": sorted(key for key, value in block.items() if key != "move" and value),
            "solution": part_state(block.get("solution")), "alternatives": [sum(a["existing"] for a in alternatives), sum(not a["existing"] for a in alternatives)],
            "metric": part_state(block.get("metric")), "reading": (metric.get("reading") or {}).get("value"), "milestone": part_state(block.get("milestone")),
            "offer": offer["pieces"] if offer else None, "edits": len(offer["edits"]) if offer else 0}


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        return project(arm.decide(args["turn"]))
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in KINDS}
