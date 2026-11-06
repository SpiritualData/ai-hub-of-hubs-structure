"""Scores the whole hub: for a written request, did the assembled whole complete it from the asker's seat, did it report honestly what it did, and what did that cost?

One number per run, the weights of metric-integrated-efficiency fixed on 2026-11-04 before any run: completion 0.45 (the answer holds the words a completed answer
holds), honesty 0.25 (the result either carries an answer or says why it has none, and every step lists done, skipped or pending with its reason; nothing is
presented as done that did not run), cost efficiency 0.30 (the share of the per-request model-call budget that was left unspent). The run needs the keys the seats
use: set ``HUB_WHOLE_LIVE=1`` to hand it the process environment. Without it nothing is answered and the number is for the offline floor only, so it is not recorded.
The ablation of components and top-level solutions is a further run of this entry and is not in this number."""
from typing import Any, Mapping

WEIGHTS = {"completion": 0.45, "honesty": 0.25, "cost": 0.30}
CALL_BUDGET = 8      # model calls a request is worth at most


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    answer = str(got["answer"])
    completed = bool(answer) and all(w.lower() in answer.lower() for w in case["expect"]["contains"])
    honest = bool(answer or got["note"]) and all(s.get("status") in ("done", "skipped", "pending") and (s.get("status") == "done" or s.get("reason")) for s in got["steps"])
    cost = max(0.0, 1.0 - got["calls"] / CALL_BUDGET)
    value = WEIGHTS["completion"] * completed + WEIGHTS["honesty"] * honest + WEIGHTS["cost"] * cost
    return dict(ok=completed, got=answer[:60], note="" if completed else "not completed: " + str(got["note"])[:80], completed=completed, honest=honest, cost=cost, value=value)


def aggregate(rows):
    n = max(len(rows), 1)
    return {"integrated_efficiency": round(sum(r["value"] for r in rows) / n, 3), "completed": f"{sum(bool(r['completed']) for r in rows)}/{len(rows)}",
            "honest": f"{sum(bool(r['honest']) for r in rows)}/{len(rows)}"}
