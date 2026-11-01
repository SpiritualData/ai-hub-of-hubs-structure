"""docs/how-to/register-a-second-consumer.md is run, so it cannot rot."""
import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402


def test_the_quickstart_runs_and_prints_the_reasons():
    code = re.search(r"```python\n(.*?)```", (ROOT / "docs" / "how-to" / "register-a-second-consumer.md").read_text(), re.S).group(1)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, "quickstart", "exec"), {"__name__": "quickstart"})
    lines = out.getvalue().splitlines()
    assert lines[0].startswith("[Card(id='a'") and "second consumer" in lines[0]
    assert lines[1].startswith("card-store -> my-list-store (layer: consumer selections, package version ")
    assert lines[2].startswith("card-store -> local_card_store (layer: hubofhubs default, package version ")
    assert not re.search(r"quest|qar", code, re.I)


def test_the_one_line_section_is_true():
    import hubofhubs
    text = (ROOT / "docs" / "how-to" / "register-a-second-consumer.md").read_text()
    assert "hubofhubs.assemble(environ=os.environ)" in text and "arms=" in text
    system = hubofhubs.assemble()
    assert "card-store" in system and "call-a-model" in system and "model-call" in system
    keyed = hubofhubs.assemble(arms={"call-a-model": "anthropic"}, environ={"ANTHROPIC_API_KEY": "not-a-real-key"})
    assert "model-call" in keyed and "ANTHROPIC_API_KEY" in hubofhubs.assemble(arms={"call-a-model": "anthropic"}).pending["call-a-model"]
