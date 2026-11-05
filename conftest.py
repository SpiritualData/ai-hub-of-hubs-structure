"""Shared by every test, in tests/ and in the tests/ folders beside each solution: puts the hub and the shared test support (tests/support.py,
tests/act_support.py, tests/fixtures) on the path, and keeps the process-wide esoi registry as each test found it: registrations made in a test do not outlive it, and neither\ndoes an arm module imported in a test."""
import sys
from pathlib import Path

import pytest
from esoi import selection

ROOT = Path(__file__).resolve().parent
for entry in (ROOT / "tests", ROOT):
    sys.path.insert(0, str(entry))
from hubofhubs import HUB  # noqa: E402

HUB.prepare()  # declares every seat once, before any test snapshots the registry


@pytest.fixture(autouse=True)
def restore_registry():
    modules = set(sys.modules)
    before = {k: (dict(e.implementations), set(e.replaced), e.interface, e.origin) for k, e in selection.REGISTRY.items()}
    yield
    for name in [m for m in sys.modules if m not in modules and m.split(".")[0] == "hubofhubs"]:
        sys.modules.pop(name)   # an arm module imported in a test declares itself again when the next test imports it
    for key in [k for k in selection.REGISTRY if k not in before]:
        selection.REGISTRY.pop(key)
    for key, (impls, replaced, interface, origin) in before.items():
        entry = selection.REGISTRY[key]
        entry.implementations, entry.replaced, entry.interface, entry.origin = dict(impls), set(replaced), interface, origin
