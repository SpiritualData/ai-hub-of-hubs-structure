"""docs/quickstart.md is run, so it cannot rot."""
import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402


def test_the_quickstart_runs_and_prints_the_reasons():
    code = re.search(r"```python\n(.*?)```", (ROOT / "docs" / "quickstart.md").read_text(), re.S).group(1)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, "quickstart", "exec"), {"__name__": "quickstart"})
    lines = out.getvalue().splitlines()
    assert lines[0].startswith("[Card(id='a'") and "second consumer" in lines[0]
    assert lines[1].startswith("card-store -> my-list-store (layer: consumer selections, package version ")
    assert lines[2].startswith("card-store -> local_card_store (layer: hubofhubs default, package version ")
    assert not re.search(r"quest|qar", code, re.I)
