"""docs/tutorials/assemble-and-run-your-first-seat.md is run, so it cannot rot."""
import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402


def test_the_tutorial_runs_and_prints_what_it_says():
    text = (ROOT / "docs" / "tutorials" / "assemble-and-run-your-first-seat.md").read_text()
    code = "\n".join(re.findall(r"```python\n(.*?)```", text, re.S))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, "tutorial", "exec"), {"__name__": "tutorial"})
    lines = out.getvalue().splitlines()
    assert "call-a-model" in lines[0] and "search-backend" in lines[0] and "act-in-the-world" in lines[0]
    assert lines[1].startswith("[Card(id='first'") and lines[2] == "1"
    assert lines[3].startswith("card-store -> local_card_store (layer: hubofhubs default")
