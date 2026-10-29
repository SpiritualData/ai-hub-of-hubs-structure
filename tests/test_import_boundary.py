"""Every import in the hub package is the standard library, the package itself or esoi.

An allowlist, not a deny list of consumer names: any other top-level module fails, whatever its name.
Third-party arms live in extras and are loaded lazily by name, never imported at module level here.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIRS = ("hubofhubs",)
ALLOWED = set(sys.stdlib_module_names) | set(PACKAGE_DIRS) | {"esoi"}


def top_level_imports(source: str) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def offenders(source: str) -> set[str]:
    return top_level_imports(source) - ALLOWED


def test_every_package_import_is_allowed():
    files = [p for d in PACKAGE_DIRS if (ROOT / d).is_dir() for p in (ROOT / d).rglob("*.py")]
    assert files, "no package files found"
    bad = {str(p.relative_to(ROOT)): sorted(offenders(p.read_text())) for p in files if offenders(p.read_text())}
    assert not bad, f"imports outside stdlib, the package and esoi: {bad}"


def test_checker_rejects_unlisted_modules():
    assert offenders("import requests") == {"requests"}
    assert offenders("from quest_ai_runner.core import x") == {"quest_ai_runner"}
    assert offenders("import json, esoi.runtime\nfrom . import registry\nfrom hubofhubs import a") == set()
    assert offenders("def f():\n    import numpy") == {"numpy"}  # function-level imports count too
