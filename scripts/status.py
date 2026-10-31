"""Rewrite the generated blocks from the records: the seat summary, the evidence table and the list of what is not measured yet in
README.md, the area detail in docs/registry.md, and every arm of every check in docs/evidence-by-arm.md. The evidence comes from
esoi/results.csv, esoi/per_case.csv and esoi/evidence.csv (hubofhubs/evidence_summary.py); nothing is typed by hand.
Run: python3 scripts/status.py [--check]. The README shows one row per seat so it does not grow with the registry; the detail
file lists every area."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from esoi import config as esoi_config  # noqa: E402
from esoi import registry as esoi_registry  # noqa: E402
from esoi.tables import read_csv  # noqa: E402
from hubofhubs import evidence_summary, render_docs  # noqa: E402

TARGETS = (("README.md", render_docs.STATUS_BEGIN, render_docs.STATUS_END),
           ("docs/registry.md", render_docs.DETAIL_BEGIN, render_docs.DETAIL_END),
           ("README.md", evidence_summary.EVIDENCE_BEGIN, evidence_summary.EVIDENCE_END),
           ("README.md", evidence_summary.UNMEASURED_BEGIN, evidence_summary.UNMEASURED_END),
           ("docs/evidence-by-arm.md", evidence_summary.ARMS_BEGIN, evidence_summary.ARMS_END))


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


def records():
    config = esoi_config.load(ROOT / "esoi.toml")
    return config, esoi_registry.load(config)


def blocks():
    config, registry = records()
    return {render_docs.STATUS_BEGIN: build(), render_docs.DETAIL_BEGIN: build_detail(),
            evidence_summary.EVIDENCE_BEGIN: evidence_summary.evidence_block(config, registry, ROOT),
            evidence_summary.UNMEASURED_BEGIN: evidence_summary.unmeasured_block(config, registry, ROOT),
            evidence_summary.ARMS_BEGIN: evidence_summary.arms_block(config, registry)}


def main(argv):
    stale = False
    made = blocks()
    for name, begin, end in TARGETS:
        path = ROOT / name
        text = path.read_text()
        new = render_docs.rewrite(text, begin, end, made[begin])
        stale = stale or new != text
        if "--check" not in argv:
            path.write_text(new)
    return 1 if stale and "--check" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
