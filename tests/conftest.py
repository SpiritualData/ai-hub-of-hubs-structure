"""Keep the process-wide esoi registry as each test found it: registrations made in a test do not outlive it."""
import sys
from pathlib import Path

import pytest
from esoi import runtime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hubofhubs.seats  # noqa: E402,F401  (declared once, before any test snapshots the registry)
import hubofhubs.tiers  # noqa: E402,F401


@pytest.fixture(autouse=True)
def restore_registry():
    before = {k: (dict(e.implementations), set(e.replaced), e.interface, e.origin) for k, e in runtime.REGISTRY.items()}
    yield
    for key in [k for k in runtime.REGISTRY if k not in before]:
        runtime.REGISTRY.pop(key)
    for key, (impls, replaced, interface, origin) in before.items():
        entry = runtime.REGISTRY[key]
        entry.implementations, entry.replaced, entry.interface, entry.origin = dict(impls), set(replaced), interface, origin
