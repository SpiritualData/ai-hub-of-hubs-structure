"""Write (or with ``--check`` only check) ``hubofhubs/arm_order.json``: the arms of every solution, best-measured first.

The order is the leaderboard of ``esoi/results.csv`` read the way ``Assembler.metric_order`` reads it. An installed copy has no records or
results, so the order ships with the package; the hub uses it to put the best arm that can run on a machine in place of a selected arm that cannot
(``hubofhubs/the_self/assembler/availability.py``). Availability only chooses among measured arms in this order, never by preference.

    python3 scripts/sync_arm_order.py          # rewrite
    python3 scripts/sync_arm_order.py --check  # exit 1 when not current"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from esoi import Assembler  # noqa: E402

from hubofhubs.the_self.assembler.resolution import PACKAGE_DIR, SCOPE, interface_modules  # noqa: E402

TARGET = ROOT / "hubofhubs" / "arm_order.json"


def order() -> dict:
    hub = Assembler(SCOPE, PACKAGE_DIR, modules=interface_modules(), records=ROOT)
    selection = json.loads((PACKAGE_DIR / "esoi_selection.json").read_text())
    found = {}
    for solution in sorted(key for key in selection if key != "@intents"):
        names = hub.metric_order(solution, "")[0]
        if len(names) > 1:
            found[solution] = list(names)
    return found


def main(argv=None) -> int:
    text = json.dumps(order(), indent=1, sort_keys=True) + "\n"
    if "--check" in (argv if argv is not None else sys.argv[1:]):
        if TARGET.is_file() and TARGET.read_text() == text:
            print("arm_order.json is current")
            return 0
        print("arm_order.json is not current: run python3 scripts/sync_arm_order.py", file=sys.stderr)
        return 1
    TARGET.write_text(text)
    print("arm_order.json written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
