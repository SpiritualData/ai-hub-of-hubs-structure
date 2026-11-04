"""The conditions a stage of ``metric-retrieve-context`` checks before an arm may pass it (the cascade's ``when`` texts name this command).

The esoi cascade's own gates are ``all-pass`` and ``competitive`` on the one balanced number; they cannot say "wins one kind while losing another" or
"reads the whole source per request". These checks read the newest complete run of each arm from the run log ``esoi/runs.csv`` (the per-case rows the scorer writes) and
state each result:

* **cases**: every row was scored on the same case set (one ``cases_sha``), and each kind present holds at least ``mix.MIN_CASES`` cases (the new kinds
  count only then); the three pinned datasets load and match their sha256 (memory sample, public repositories, their cases and history).
* **kinds**: the challenger's mean utility on every kind is at least the held arm's minus ``mix.KIND_TOLERANCE``: an arm that wins on the mix by
  winning one kind and losing another beyond that does not pass.
* **risk**: no request read more than ``mix.MAX_SOURCE_CALLS`` source calls, none read more than ``mix.MAX_SCAN_SHARE`` of the records of its corpus
  (no full scan per request), and nothing was read or returned outside the request's allowed scope (``mix.MAX_OUT_OF_SCOPE``).

    PYTHONPATH=.:evaluation:../evolvable-structure/implementations/python python3 evaluation/context_retrieval/gate.py [--held ARM] [ARM ...]

Without arms it checks every arm recorded on the newest case set. It prints one line per check and exits 1 when any arm fails a check.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_retrieval import memory, mix, open_code  # noqa: E402

RUNS = Path(__file__).resolve().parents[2] / "esoi" / "runs.csv"
HELD = "abstaining_hybrid"
ARMS_IGNORED_BY_KIND_GATE = ("live_scan",)     # a diagnostic bound; it is still held to the risk gates, which it fails by design


def latest(path: Path = RUNS) -> dict:
    """``{arm: (case-set id, details dict)}`` for the newest complete run of each arm on the newest case set. The details of ``esoi/results.csv`` are
    cut short, so the per-case rows of the run log (``esoi/runs.csv``, local) are read and aggregated by the scorer's own ``aggregate``."""
    import hashlib
    import json
    from context_retrieval import score
    runs: dict = {}
    for r in csv.DictReader(path.open()):
        if r["component"] == "context_retrieval" and r["kind"] == "case" and r["row"]:
            runs.setdefault((r["run_id"], r["impl"]), []).append(json.loads(r["row"]))
    out = {}
    for (run_id, impl), rows in sorted(runs.items()):
        ids = sorted(str(x["id"]) for x in rows)
        if "kind" in rows[0] and not any(x.get("note", "").startswith(("OfflineViolation", "ModuleNotFound")) for x in rows):
            out[impl] = (f"{hashlib.sha256(','.join(ids).encode()).hexdigest()[:8]}/{len(ids)}", rows)
    if not out:
        return {}
    newest = max((v[0] for v in out.values()), key=lambda c: int(c.split("/")[1]))
    return {impl: (sha, score.aggregate(rows)) for impl, (sha, rows) in out.items() if sha == newest}


def datasets_in_place() -> list:
    """What is wrong with the pinned datasets (empty when the memory sample, the cases and history of the public repositories load and match their pins)."""
    problems = []
    try:
        memory._SAMPLE.clear()
        memory.sample()
        open_code.cases()
        open_code.checked(open_code.HISTORY_FILE, "history_sha256", "commits")
    except Exception as exc:    # noqa: BLE001
        problems.append(f"{type(exc).__name__}: {exc}")
    return problems


def check(arms: dict, held: str = HELD) -> list:
    """``[(arm, check, ok, text)]`` for every arm in ``arms`` against ``held``."""
    results = []
    shas = {sha for sha, _ in arms.values()}
    problems = datasets_in_place()
    results.append(("*", "pins", not problems, "; ".join(problems) or "memory sample, public-repository cases and history match their sha256"))
    results.append(("*", "same-cases", len(shas) == 1, f"{len(arms)} arms on {len(shas)} case set(s)"))
    base = arms.get(held, (None, {}))[1]
    for arm, (_, d) in arms.items():
        counts = dict(p.split(":") for p in d.get("cases_by_kind", "").split("/") if ":" in p)
        short = [f"{k} {counts.get(k, 0)} < {n}" for k, n in mix.MIN_CASES.items() if int(counts.get(k, 0)) < n]
        results.append((arm, "min-cases", not short, "; ".join(short) or "every new kind has its minimum")
                       )
        if arm != held and arm not in ARMS_IGNORED_BY_KIND_GATE and base:
            worse = [f"{k} {float(d[k + '_utility']):.3f} < {float(base[k + '_utility']):.3f} - {mix.KIND_TOLERANCE}"
                     for k in counts if k + "_utility" in d and k + "_utility" in base and float(d[k + "_utility"]) < float(base[k + "_utility"]) - mix.KIND_TOLERANCE]
            results.append((arm, "kinds", not worse, "; ".join(worse) or f"no kind trails {held} by more than {mix.KIND_TOLERANCE}"))
        calls, scan, outside = int(float(d.get("source_calls_max", 0))), float(d.get("scan_share_max", 0)), int(float(d.get("out_of_scope", 0)))
        results.append((arm, "source-calls", calls <= mix.MAX_SOURCE_CALLS, f"max {calls} per request, limit {mix.MAX_SOURCE_CALLS}"))
        results.append((arm, "no-full-scan", scan <= mix.MAX_SCAN_SHARE, f"largest share of a corpus read in one request {scan}, limit {mix.MAX_SCAN_SHARE}"))
        results.append((arm, "scope", outside <= mix.MAX_OUT_OF_SCOPE, f"{outside} records read or returned outside the request's scope"))
    return results


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    held = argv[argv.index("--held") + 1] if "--held" in argv else HELD
    names = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--held")]
    arms = {k: v for k, v in latest().items() if not names or k in names or k == held}
    failed = False
    for arm, name, ok, text in check(arms, held):
        failed |= not ok
        print(f"{'PASS' if ok else 'FAIL'} {arm:26} {name:13} {text}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
