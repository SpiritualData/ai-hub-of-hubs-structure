"""Scores a Role Understanding arm: does it state a part's role as the records give it, and does it report the contradictions a role has with what its code does?

Two kinds of case (``build_cases.py`` names each origin): ``record`` (the role fields of a written row, verbatim, and a part no record knows, which must come back
unstated) and ``contradiction`` (a written set of records and code in which an honest checker reports exactly the expected codes, and a consistent twin reports
none). A record case compares the role fields; a contradiction case compares the codes an arm reports, and an arm that reports no contradictions field reports
none. One number: the share of cases that match, balanced with cost and time by ``[balance.role_understanding]`` (accuracy 70%, cost 15%, time 15%, fixed before
any arm was scored). No model call, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

FIELDS = ("part", "stated", "purpose", "out_of_scope", "delegates_to")


def adapt(implementation, meter):
    def run(kind, args):
        if kind == "record":
            return implementation(solutions=args["solutions"], implementations=[], code={}).state_role(args["part"])
        arm = implementation(solutions=args["solutions"], implementations=args["implementations"], code=args["code"])
        return arm.state_role(args["part"])
    return run


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    if case["kind"] == "record":
        shown = {k: got.get(k) for k in FIELDS if k in case["expect"]}
    else:
        shown = {"contradictions": sorted(c["code"] for c in got.get("contradictions", []))}
    return dict(judge(shown, case), kind=case["kind"])


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}" for k in ("record", "contradiction")}
