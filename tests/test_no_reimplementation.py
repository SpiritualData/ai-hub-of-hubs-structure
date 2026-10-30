"""The hub must not grow generic assembly again: that belongs in the esoi library (esoi docs: what-belongs-where.md)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERIC_MODULES = {"assembly.py", "graph.py", "needs.py", "config.py"}   # the modules this repository used to hold


def test_the_generic_assembly_modules_are_gone():
    assert not GENERIC_MODULES & {p.name for p in (ROOT / "hubofhubs").iterdir()}
