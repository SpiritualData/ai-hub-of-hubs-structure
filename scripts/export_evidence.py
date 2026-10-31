"""Write (or with --check, verify) esoi/evidence.csv, the esoi library's view of the public evidence registry.

hubofhubs/registry/hub_evidence.csv is the one source of truth. The library reads a file with one fixed header and no `area` or
`seat` column, so this derives it: every row, every other column unchanged and in the library's order, except rows with no value (below). Edit the registry, never
the derived file.

A row with no value (a direction only, the ranking carried in its note) cannot be graded and the library refuses an empty value, so
the export leaves it out; it stays in the registry as a sourced direction and `omitted_ids()` names it.

One value is rewritten: a comma in a candidate name becomes a space, because the library joins candidate keys with commas and a
name that holds one would never match its implementation. The registry keeps the name as the findings spell it.

    python3 scripts/export_evidence.py --check   # exit 1 when esoi/evidence.csv is not the export
    python3 scripts/export_evidence.py           # rewrite esoi/evidence.csv
"""
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "hubofhubs" / "registry" / "hub_evidence.csv"
TARGET = ROOT / "esoi" / "evidence.csv"
DROPPED = ("area", "seat")


def library_candidate(name):
    """The candidate as the library reads it: no comma in the name."""
    return " ".join(name.replace(",", " ").split())


def export_text(source=SOURCE):
    """The derived file's text: the registry's rows without the area and seat columns."""
    with open(source, newline="") as handle:
        reader = csv.DictReader(handle)
        columns = [c for c in reader.fieldnames if c not in DROPPED]
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            if row["value"].strip():
                row["candidate"] = library_candidate(row["candidate"])
                writer.writerow(row)
    return out.getvalue()


def omitted_ids(source=SOURCE):
    """The evidence ids the export leaves out because they carry a direction and no value."""
    with open(source, newline="") as handle:
        return [r["evidence_id"] for r in csv.DictReader(handle) if not r["value"].strip()]


def main(argv):
    text = export_text()
    if "--check" in argv:
        have = TARGET.read_text() if TARGET.is_file() else ""
        if have != text:
            print(f"{TARGET.relative_to(ROOT)} is not the export of {SOURCE.relative_to(ROOT)}; run python3 scripts/export_evidence.py")
            return 1
        return 0
    TARGET.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
