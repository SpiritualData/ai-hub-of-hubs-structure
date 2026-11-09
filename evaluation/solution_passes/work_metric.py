"""The work-outcome metric of Solution Passes (metric-solution-passes-work-outcome), per arm: score = B - 0.5 N - 0.1 L - 0.1 K, with the
weights and constants fixed in the metric record before any arm was run.

    python evaluation/solution_passes/work_metric.py free              # the deciding record reaches the brief; nothing reaches it on abstain cases
    python evaluation/solution_passes/work_metric.py one               # one work case, cheap tier, every arm
    python evaluation/solution_passes/work_metric.py all [REPS]        # every work and abstain case, cheap tier, every arm
    ... [REPS] [OUT.json] [RECORDS_ROOT CASES.json]                   # a consumer's own public records and cases of the same shape"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from solution_passes.score import work_case      # noqa: E402

ARMS = ("off", "always", "gated")
NOISE_WEIGHT, LATENCY_WEIGHT, CALL_WEIGHT = 0.5, 0.1, 0.1
LATENCY_BUDGET_SECONDS, CALL_BUDGET = 600.0, 40.0
CASES = json.loads((Path(__file__).resolve().parent / "cases.json").read_text())


def p90(values):
    ordered = sorted(values)
    return ordered[max(0, int(round(0.9 * len(ordered))) - 1)] if ordered else 0.0


def score(rows):
    work = [r for r in rows if r["kind"] == "work"]
    abstain = [r for r in rows if r["kind"] == "abstain"]
    b = sum(bool(r.get("met")) for r in work) / len(work) if work else 0.0
    n = sum(bool(r["block"] or r["calls"]) for r in abstain) / len(abstain) if abstain else 0.0
    secs = [r["seconds"] for r in rows]
    latency = (0.25 * statistics.median(secs) + 0.75 * p90(secs)) / LATENCY_BUDGET_SECONDS if secs else 0.0
    calls = (sum(r["calls"] for r in rows) / len(rows)) / CALL_BUDGET if rows else 0.0
    return {"B": round(b, 3), "N": round(n, 3), "L": round(latency, 4), "K": round(calls, 4),
            "score": round(b - NOISE_WEIGHT * n - LATENCY_WEIGHT * latency - CALL_WEIGHT * calls, 4),
            "median_s": round(statistics.median(secs), 2) if secs else 0, "p90_s": round(p90(secs), 2), "calls_per_case": round(sum(r["calls"] for r in rows) / len(rows), 2) if rows else 0}


def run(stage, reps=1, root=None, cases=None):
    chosen = [c for c in (cases or CASES) if c["kind"] in ("work", "abstain")]
    if stage == "one":
        chosen = [c for c in chosen if c["kind"] == "work"][:1]
    out = {}
    for arm in ARMS:
        rows = []
        for _ in range(reps):
            for case in chosen:
                args = {"request": case["args"]["request"], "requirements": case["expect"].get("requirements") or []}
                got = work_case(None, args, arm, real=stage != "free", root=root)
                row = {"id": case["id"], "kind": case["kind"], "block": bool(got["block"]), "calls": got["calls"], "seconds": got["seconds"],
                       "reached": case["expect"].get("record", "") in got["block"] if case["kind"] == "work" else None}
                if stage != "free" and case["kind"] == "work":
                    row["met"] = bool(got["checked"]["met"])
                    row["rubric"] = got["checked"]["score"]
                    row["output"] = got["output"][:600]
                rows.append(row)
                print(arm, {k: v for k, v in row.items() if k != "output"}, flush=True)
        if stage == "free":
            work = [r for r in rows if r["kind"] == "work"]
            out[arm] = {"reached": f"{sum(bool(r['reached']) for r in work)}/{len(work)}",
                        "abstain_clean": f"{sum(not r['block'] for r in rows if r['kind'] == 'abstain')}/{sum(r['kind'] == 'abstain' for r in rows)}"}
        else:
            out[arm] = score(rows)
        out[arm + "_rows"] = rows
    return out


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "free"
    root = sys.argv[4] if len(sys.argv) > 4 else None
    cases = json.loads(Path(sys.argv[5]).read_text()) if len(sys.argv) > 5 else None
    result = run(stage, int(sys.argv[2]) if len(sys.argv) > 2 else 1, root, cases)
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("_rows")}, indent=1))
    target = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    if target:
        target.write_text(json.dumps(result, indent=1))
