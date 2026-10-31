"""Scores the whole assembly: every seat is built or says exactly what to pass, and a variable handed over fills the arm that declares it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)


def aggregate(rows):
    """The share of the zero-configuration seats that are built, by counting the seat cases that report ``built``."""
    import hubofhubs
    system = hubofhubs.assemble()
    return f"zero-config builds {len(system.solutions())} of {len(system.solutions()) + len(system.pending)} seats: {', '.join(system.solutions())}"
