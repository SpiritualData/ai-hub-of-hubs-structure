"""Re-score recorded rows of chosen components after their ``[balance.<component>]`` table changed (the skill: encode the reason, then re-score every arm).

The balanced number is a pure function of what a row already records (cases, passed, cost, seconds) and the table, so nothing is re-run. Only the
``balanced`` cell of each results row and the ``score`` cell of each per-case row of the named components are rewritten, through esoi's own
``balance`` functions; every other cell and row is kept as it is. The files are read again just before writing and the write is refused when
another process changed them in between (recording appends).

    python3 scripts/rescore_balanced.py agent_sessions agent_sessions_hard           # rewrite
    python3 scripts/rescore_balanced.py agent_sessions agent_sessions_hard --check   # exit 1 when a row would change"""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from esoi.optimization.measurement_harness import balance  # noqa: E402
from esoi.structure.intent_registry.config import load as load_config  # noqa: E402


def read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames), list(reader)


def write(path, header, rows, stamp):
    if path.stat().st_mtime_ns != stamp:
        raise SystemExit(f"{path.name} changed while it was being re-scored: run again")
    temporary = path.with_suffix(".rescore")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def rescored_results(rows, tables):
    changed = 0
    for row in rows:
        table = tables.get(row["component"])
        if table is None or row["cost_usd"] == "" or not row["cases"]:
            continue
        found = balance.balanced(int(float(row["passed"])), int(float(row["cases"])), row["cost_usd"], float(row["seconds"]), table)
        if found and str(found["balanced"]) != row["balanced"]:
            row["balanced"] = str(found["balanced"])
            changed += 1
    return changed


def rescored_cases(rows, results, tables):
    """A run's per-case scores use the run's cost shared equally over its cases (no tokens are counted per case)."""
    runs = {}
    for row in rows:
        runs.setdefault((row["component"], row["impl"], row["cases_sha"], row["sample"]), []).append(row)
    cost_of = {(r["component"], r["impl"], r["cases_sha"], r["sample"]): r["cost_usd"] for r in results if r["cost_usd"] != ""}
    changed = 0
    for key, group in runs.items():
        table = tables.get(key[0])
        if table is None or key not in cost_of:
            continue
        share = [float(cost_of[key]) / len(group)] * len(group)
        scores = balance.case_scores([r["ok"] == "1" for r in group], share, [float(r["seconds"]) for r in group], table)
        for row, score in zip(group, scores):
            if str(score) != row["score"]:
                row["score"] = str(score)
                changed += 1
    return changed


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    check = "--check" in args
    components = [a for a in args if not a.startswith("--")]
    config = load_config(start=ROOT)
    tables = {c: config.balance[c] for c in components}
    results_path, per_case_path = ROOT / "esoi" / "results.csv", ROOT / "esoi" / "per_case.csv"
    stamps = (results_path.stat().st_mtime_ns, per_case_path.stat().st_mtime_ns)
    header_r, results = read(results_path)
    header_c, cases = read(per_case_path)
    changed_r = rescored_results(results, tables)
    changed_c = rescored_cases([r for r in cases if r["component"] in tables], results, tables)
    print(f"{changed_r} results rows and {changed_c} per-case rows would change" if check else f"{changed_r} results rows and {changed_c} per-case rows re-scored")
    if check:
        return 1 if changed_r or changed_c else 0
    if changed_r:
        write(results_path, header_r, results, stamps[0])
    if changed_c:
        write(per_case_path, header_c, cases, stamps[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
