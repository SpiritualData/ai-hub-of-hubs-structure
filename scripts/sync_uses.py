"""Write (or with --check, verify) the uses_solution_ids column of the implementations.csv records from the constructor parameters
typed with a seat Protocol, and check the graph (no cycles, every need resolves or is consumer-provided). The work is the
library's (``esoi.assemble``); this binds it to the hub's records.

    python3 scripts/sync_uses.py --check     # exit 1 and print each disagreement
    python3 scripts/sync_uses.py             # rewrite the column
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from esoi import intents  # noqa: E402
from hubofhubs.resolution import HUB  # noqa: E402

NO_CODE = set()


def recorded_without_code():
    """Ids of recorded alternatives that name no code (`filepath` empty: a described option, "no arm yet"). They have no
    constructor to read, so there is nothing to compare their `uses_solution_ids` with."""
    rows = intents.read_tree(ROOT / "esoi", "implementations.csv")
    return {row["implementation_id"] for row in rows if not row.get("filepath", "").strip()}


def main(argv):
    global NO_CODE
    NO_CODE = recorded_without_code()
    if "--check" in argv:
        bad = HUB.uses_problems(ROOT / "esoi")
        bad = [line for line in bad if line.split(":", 2)[0] + ":" + line.split(":", 2)[1] not in NO_CODE]
        if bad:
            print("\n".join(bad))
        return 1 if bad else 0
    HUB.sync_uses(ROOT / "esoi")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
