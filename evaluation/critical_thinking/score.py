"""Scores the pursue step of a Critical Thinking arm: for a draft whose goal condition is unmet, does it end as it should?

Each case scripts the check (outcome text to met) and the attempts the stub returns, with read and write means and a budget. The summary compared is the
status, whether the goal was met, the replans used, the means tried, how many interim lines were announced, how many attempts ran, how many write means
were offered to an attempt, whether a plain message came back, the outcome to send and how many writes were ignored. One number: the share of cases whose
summary equals the expected one. No model call.

Private inputs that were handled badly (a JSONL file named by ``HUB_POORLY_ANSWERED_INPUTS``, kept outside any repository) add one case each when the
variable is set: the input is the goal of an unmet first draft with one untried read that meets it, built in memory and never written anywhere."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

PRIVATE = "HUB_POORLY_ANSWERED_INPUTS"


def private_cases(environ=None):
    """One in-memory case per row of the private set named by the environment, or none."""
    path = (os.environ if environ is None else environ).get(PRIVATE, "")
    if not path or not Path(path).is_file():
        return []
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line) if line.strip() else {}
        if row.get("input_text"):
            args = {"goal": row["input_text"], "done_standard": "the input is handled", "draft": "draft", "verdicts": {"draft": False, "better": True},
                    "means": [{"name": "search", "kind": "read", "cost_seconds": 5}], "attempts": [{"outcome": "better", "means_used": ["search"]}],
                    "budget": {"max_replans": 2, "wall_seconds": 120, "inline_seconds": 30, "background": False}, "attempt_given": True, "elapsed_start": 0}
            cases.append({"id": "private-" + str(row.get("case_id")), "kind": "private", "args": args,
                          "expect": {"status": "met_after_replan", "met": True, "replans": 1, "tried": ["search"], "interims": 0, "attempts": 1, "writes_offered": 0,
                                     "message": False, "outcome": "better", "ignored_writes": 0}})
    return cases


def adapt(implementation, meter):
    def run(kind, args):
        arm = implementation(None, None, None, None)
        clock = {"t": float(args["elapsed_start"])}
        seen = {"interims": 0, "attempts": 0, "writes_offered": 0}
        queue = list(args["attempts"])
        costs = {m["name"]: float(m["cost_seconds"]) for m in args["means"]}

        def check(outcome):
            scripted = args["verdicts"].get(outcome if isinstance(outcome, str) else "", False)
            if scripted == "awaiting":          # the draft is the one question a cut-off or ambiguous message needs: a structured flag, not its words
                return {"met": False, "awaiting_person": True, "reason": "the person supplies the missing piece"}
            met = bool(scripted)
            return {"met": met, "reason": "" if met else "the transcript is not used"}

        def attempt(step):
            seen["attempts"] += 1
            seen["writes_offered"] += sum(1 for name in step["means"] if next((m for m in args["means"] if m["name"] == name), {}).get("kind") == "write")
            result = queue.pop(0) if queue else {"outcome": "", "means_used": []}
            clock["t"] += sum(costs.get(n, 0.0) for n in step["means"])
            return result

        def announce(text):
            seen["interims"] += 1

        budget = dict(args["budget"], elapsed=lambda: clock["t"])
        got = arm.pursue(args["goal"], args["done_standard"], args["draft"], attempt if args["attempt_given"] else None, args["means"], budget, announce, check)
        return {"status": got["status"], "met": bool(got["met"]), "replans": got["replans"], "tried": list(got["tried"]), "interims": seen["interims"],
                "attempts": seen["attempts"], "writes_offered": seen["writes_offered"], "message": bool(got["message"]), "outcome": got["outcome"],
                "ignored_writes": len(got["ignored_writes"])}
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])
