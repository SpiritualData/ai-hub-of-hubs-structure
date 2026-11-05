"""docs/how-to/adopt-the-hub.md is run, so it cannot rot."""
import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402


def test_the_adopt_the_hub_how_to_runs_and_prints_what_it_says():
    text = (ROOT / "docs" / "how-to" / "adopt-the-hub.md").read_text()
    code = "\n".join(re.findall(r"```python\n(.*?)```", text, re.S))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, "how-to", "exec"), {"__name__": "how_to"})
    lines = out.getvalue().splitlines()
    assert len(lines) == 5
    assert lines[0].startswith("['S53 note-search: the library hub has no solution no-such-solution']")
    assert lines[1:] == ["True", "n1", "['n2', 'n1']", "['n1', 'n2']"]
