"""The base install carries what the selected arms need: ``pip install hubofhubs`` works with no extra."""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from support import ROOT  # noqa: E402

from esoi import requirements as needs  # noqa: E402
from esoi import AssemblyConfig  # noqa: E402

from hubofhubs import assembler  # noqa: E402
from hubofhubs.the_self.integrity import base_dependencies  # noqa: E402

DISTRIBUTION_OF = {"google.genai": "google-genai", "qdrant_client": "qdrant-client", "Stemmer": "PyStemmer", "acp": "agent-client-protocol", "graphify": "graphifyy", "sklearn": "scikit-learn"}


def base():
    return [re.split(r"[<>=!~\[ ;@]", spec, maxsplit=1)[0].strip().lower().replace("_", "-")
            for spec in tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]]


def test_every_required_python_need_of_a_selected_arm_is_in_the_base_dependencies():
    missing = []
    for member in assembler().closure(AssemblyConfig(), None, (), False):
        for item in needs.declared(member.target):
            if isinstance(item, needs.Python) and item.required:
                wanted = DISTRIBUTION_OF.get(item.module, item.module).lower().replace("_", "-")
                if wanted not in base():
                    missing.append(f"{member.label}: {item.module}")
    assert not missing, f"selected arms need libraries the base install lacks (run python3 scripts/sync_dependencies.py): {missing}"


def test_the_marked_dependencies_are_the_derived_ones():
    ok, _text = base_dependencies.current((ROOT / "pyproject.toml").read_text())
    assert ok, "run python3 scripts/sync_dependencies.py"


def test_a_missing_library_is_detected():
    text = (ROOT / "pyproject.toml").read_text().replace('    "google-genai>=2.8",\n', "", 1)
    ok, rewritten = base_dependencies.current(text)
    assert not ok and "google-genai" in rewritten
