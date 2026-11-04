"""The hub is a generic library: its own code never uses the word "quest" (a consumer's product).

Only words standing alone count (not "request", "question"). The registry data files name consumers on purpose and are CSVs, not
scanned. tests/test_import_boundary.py names the consumer package to forbid importing it; it lives under tests/, outside this scan.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "hubofhubs"
WORD = re.compile(r"(?<![A-Za-z])quest(?![a-z])", re.I)
ALLOWLIST: set = set()   # relative paths that may name the word, with a reason; keep empty


def test_hub_python_files_never_say_quest():
    hits = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT.parent).as_posix()
        if rel in ALLOWLIST:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if WORD.search(line):
                hits.append(f"{rel}:{n}: {line.strip()[:80]}")
    assert not hits, "the hub is generic; say 'consumer' or a generic kind:\n" + "\n".join(hits)
