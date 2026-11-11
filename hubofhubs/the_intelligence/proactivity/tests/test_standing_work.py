"""The standing work standard is a prompt constant of the public api: eight numbered points, no em dash, generic wording."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from hubofhubs.api import STANDING_WORK_STANDARD  # noqa: E402


def test_standing_work_standard_has_eight_numbered_points_and_generic_wording():
    text = STANDING_WORK_STANDARD
    assert text.startswith("STANDING WORK STANDARD.")
    assert re.findall(r"^(\d)\. [A-Z]", text, flags=re.M) == [str(n) for n in range(1, 9)]
    assert "—" not in text and "quest" not in text.lower()
