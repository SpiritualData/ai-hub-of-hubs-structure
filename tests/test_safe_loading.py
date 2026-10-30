"""The hub's side of safe loading: every module its packaged snapshot names is one of its own files, and a hostile name is
refused. The loading rules themselves (look-alike modules, hostile parent configuration, replaced arms) are tested in the
esoi library (`tests/test_assemble.py`)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import AssemblyError, resolve  # noqa: E402
from hubofhubs.resolution import HUB  # noqa: E402

SNAPSHOT = json.loads((Path(__file__).resolve().parent.parent / "hubofhubs" / "esoi_selection.json").read_text())


def test_every_module_the_snapshot_names_is_one_of_the_hubs_own_files():
    for entry in SNAPSHOT.values():
        for module in entry["modules"].values():
            assert HUB.safe_module(module) == module


@pytest.mark.parametrize("bad", ["os:system", "os.system", "../x.py", "a/b"])
def test_a_hostile_name_is_refused_before_anything_is_imported(bad):
    with pytest.raises(AssemblyError, match="rejected"):
        resolve("reason-and-answer", bad)
