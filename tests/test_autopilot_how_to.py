"""docs/how-to/build-an-autopilot-on-the-hub.md is run, so it cannot rot."""
import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402


def test_the_autopilot_how_to_runs_and_prints_what_it_says():
    text = (ROOT / "docs" / "how-to" / "build-an-autopilot-on-the-hub.md").read_text()
    code = "\n".join(re.findall(r"```python\n(.*?)```", text, re.S))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, "how-to", "exec"), {"__name__": "how_to"})
    lines = out.getvalue().splitlines()
    assert lines[0] == "['quest-events']"
    assert [line.split()[1] for line in lines[1:5]] == ["ask-7", "daily-review", "weekly-report", "on-answer"]      # the ask, the horizons shortest first, then the reactive schedule
    assert lines[5] == "['ask-7', 'daily-review', 'on-answer']" and lines[6] == "1"      # the weekly report was held back
