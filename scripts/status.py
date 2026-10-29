"""Rewrite the status block of README.md from esoi/*.csv. Run: python3 scripts/status.py [--check]."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- status:start -->", "<!-- status:end -->"


def read(name, root=ROOT):
    with open(root / "esoi" / f"{name}.csv", newline="") as handle:
        return list(csv.DictReader(handle))


def build(root=ROOT):
    solutions, impls = read("solutions", root), read("implementations", root)
    arms = {}
    for row in impls:
        arms[row["solution_id"]] = arms.get(row["solution_id"], 0) + 1
    lines = [
        f"{len(read('problems', root))} problems, {len(read('ideals', root))} ideals, "
        f"{len(solutions)} seats, {len(read('metrics', root))} draft metrics, {len(impls)} arms.",
        "",
        "| Seat | Arms | Selected by metric |",
        "|---|---|---|",
    ]
    for row in solutions:
        count = arms.get(row["solution_id"], 0)
        selected = row["selected"] or "no arm yet"
        lines.append(f"| {row['solution_id']} | {count} | {selected} |")
    return "\n".join(lines)


def rewrite(text, block):
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    return f"{head}{START}\n{block}\n{END}{tail}"


def main(argv):
    path = ROOT / "README.md"
    text = path.read_text()
    new = rewrite(text, build())
    if "--check" in argv:
        return 0 if new == text else 1
    path.write_text(new)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
