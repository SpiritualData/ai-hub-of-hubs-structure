"""Scores a Feedback Learning arm: from a person's feedback, does it propose the one edit the feedback asks for, scoped to that person, and report feedback it
cannot turn into an edit as unresolved rather than guess? One number: the share of cases whose result equals the expected edit or the expected unresolved
reason (a note kept instead of an edit fails the named cases). Written cases; real corrections from people are not in this set. No model call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    def run(kind, args):
        return implementation().learn(args["person"], args["feedback"])
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("named", "scoped", "unresolved", "noticed")}
