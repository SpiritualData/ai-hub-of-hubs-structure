"""Write (or with ``--check`` only check) the base ``dependencies`` of ``pyproject.toml`` from the arms the hub selects.

    python3 scripts/sync_dependencies.py          # rewrite the marked lines
    python3 scripts/sync_dependencies.py --check  # exit 1 when they are not current

The selected arms declare their Python needs with ``REQUIRES``; ``hubofhubs/the_self/integrity/base_dependencies.py`` derives the libraries."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hubofhubs.the_self.integrity.base_dependencies import current  # noqa: E402


def main(argv=None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    path = ROOT / "pyproject.toml"
    ok, text = current(path.read_text())
    if ok:
        print("pyproject.toml dependencies are current")
        return 0
    if check:
        print("pyproject.toml dependencies are not current: run python3 scripts/sync_dependencies.py", file=sys.stderr)
        return 1
    path.write_text(text)
    print("pyproject.toml dependencies rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
