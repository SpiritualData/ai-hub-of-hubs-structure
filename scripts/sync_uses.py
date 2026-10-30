"""Write (or with --check, verify) the uses_solution_ids column of esoi/implementations.csv from the constructor parameters
typed with a seat Protocol, and check the graph (no cycles, every need resolves or is consumer-provided). The work is the
library's (``esoi.assemble``); this binds it to the hub's records.

    python3 scripts/sync_uses.py --check     # exit 1 and print each disagreement
    python3 scripts/sync_uses.py             # rewrite the column
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hubofhubs.resolution import HUB  # noqa: E402


def main(argv):
    if "--check" in argv:
        bad = HUB.uses_problems(ROOT / "esoi")
        if bad:
            print("\n".join(bad))
        return 1 if bad else 0
    HUB.sync_uses(ROOT / "esoi")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
