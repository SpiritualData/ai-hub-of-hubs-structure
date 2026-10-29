"""Write (or with --check, verify) the uses_solution_ids column of esoi/implementations.csv from the constructor parameters
typed with a seat Protocol, and check the graph (no cycles, every need resolves or is consumer-provided).

    python3 scripts/sync_uses.py --check     # exit 1 and print each disagreement
    python3 scripts/sync_uses.py             # rewrite the column
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hubofhubs import graph  # noqa: E402


def main(argv):
    records = ROOT / "esoi"
    solutions = graph.read_rows(records, "solutions.csv")
    rows = graph.read_rows(records, "implementations.csv")
    needs = graph.declared_needs(rows)
    if "--check" in argv:
        bad = graph.problems(solutions, rows, needs)
        if bad:
            print("\n".join(bad))
        return 1 if bad else 0
    for row in rows:
        row["uses_solution_ids"] = ";".join(sorted(needs[row["implementation_id"]]))
    with open(records / "implementations.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
