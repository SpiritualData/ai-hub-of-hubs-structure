"""Rewrite the seats table of README.md from the registry. Run: python3 scripts/status.py [--check]."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hubofhubs import render_docs  # noqa: E402


def build():
    return render_docs.seat_table()


def rewrite(text, block):
    return render_docs.rewrite(text, render_docs.STATUS_BEGIN, render_docs.STATUS_END, block)


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
