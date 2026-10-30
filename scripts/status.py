"""Rewrite the generated blocks from the registry: the seat summary in README.md and the area detail in docs/registry.md.
Run: python3 scripts/status.py [--check]. The README shows one row per seat so it does not grow with the registry; the detail
file lists every area."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from esoi.tables import read_csv  # noqa: E402
from hubofhubs import render_docs  # noqa: E402

TARGETS = (("README.md", render_docs.STATUS_BEGIN, render_docs.STATUS_END),
           ("docs/registry.md", render_docs.DETAIL_BEGIN, render_docs.DETAIL_END))


def seats():
    """``(seat id, part of the mind)`` for each mind seat in ``esoi/solutions.csv``, in the file's order. A mind seat is named
    ``<id>: the <part> seat``; a seat with no researched area still appears, with 0."""
    out = []
    for row in read_csv(ROOT / "esoi" / "solutions.csv"):
        found = re.fullmatch(r"[a-z-]+: the (.+) seat", row["name"])
        if found:
            out.append((row["solution_id"], found.group(1)))
    return out


def build():
    return render_docs.seat_summary(seats=seats())


def build_detail():
    return render_docs.area_detail(seats=seats())


def rewrite(text, block):
    return render_docs.rewrite(text, render_docs.STATUS_BEGIN, render_docs.STATUS_END, block)


def blocks():
    return {"README.md": build(), "docs/registry.md": build_detail()}


def main(argv):
    stale = False
    for name, begin, end in TARGETS:
        path = ROOT / name
        text = path.read_text()
        new = render_docs.rewrite(text, begin, end, blocks()[name])
        stale = stale or new != text
        if "--check" not in argv:
            path.write_text(new)
    return 1 if stale and "--check" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
