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
# Third-party libraries of the per-arm extras (pyproject optional-dependencies), by import name. They may be imported only
# inside a function, so importing a module never needs them.
LAZY = {"httpx", "google", "trafilatura", "pypdf", "filelock", "anthropic", "openai", "mcp", "qdrant_client", "fastembed", "voyageai", "bm25s", "Stemmer", "acp", "graphify", "networkx", "numpy", "sklearn", "textual", "rich"}


def top_level_imports(source: str) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def module_level_imports(source: str) -> set[str]:
    found = set()
    for node in ast.parse(source).body:
        found |= top_level_imports(ast.unparse(node)) if isinstance(node, (ast.Import, ast.ImportFrom)) else set()
        if isinstance(node, (ast.Try, ast.If)):
            found |= {m for child in ast.walk(node) if isinstance(child, (ast.Import, ast.ImportFrom))
                      for m in top_level_imports(ast.unparse(child))}
    return found


# Third-party code kept as its authors wrote it lives in a folder named ``vendor`` (esoi treats that name as third-party too: no docstring or port rule). It may import, at module level, only the
# libraries of the extra that carries it; nothing outside a vendor folder may, which the rule above keeps enforcing for the hub's own code.
VENDOR_LIBRARIES = {"textual", "rich", "pydantic", "pygments"}


def offenders(source: str, vendor: bool = False) -> set[str]:
    if vendor:
        return top_level_imports(source) - ALLOWED - LAZY - VENDOR_LIBRARIES
    return (top_level_imports(source) - ALLOWED - LAZY) | (module_level_imports(source) & LAZY)


def in_vendor(path: Path) -> bool:
    return "vendor" in path.relative_to(ROOT).parts


def test_every_package_import_is_allowed():
    files = [p for d in PACKAGE_DIRS if (ROOT / d).is_dir() for p in (ROOT / d).rglob("*.py") if "tests" not in p.parts]   # tests beside the code may use pytest and the shared test support
    assert files, "no package files found"
    bad = {str(p.relative_to(ROOT)): sorted(offenders(p.read_text(), in_vendor(p))) for p in files if offenders(p.read_text(), in_vendor(p))}
    assert not bad, f"imports outside stdlib, the package and esoi: {bad}"


def test_each_vendor_folder_carries_its_licence_and_says_what_it_took():
    sources = sorted({p.parent for d in PACKAGE_DIRS for p in (ROOT / d).rglob("LICENSE") if in_vendor(p)} | {p.parent for d in PACKAGE_DIRS for p in (ROOT / d).rglob("README.md") if in_vendor(p)})
    assert sources, "no vendor folder found"
    for folder in sources:
        assert (folder / "LICENSE").is_file() and (folder / "README.md").is_file(), f"{folder.relative_to(ROOT)} needs its LICENSE and a README.md saying what was taken and what was cut"
        assert str(folder.relative_to(ROOT)) in (ROOT / "NOTICE").read_text(), f"{folder.relative_to(ROOT)} is not named in NOTICE"


def test_checker_rejects_unlisted_modules():
    assert offenders("import requests") == {"requests"}
    assert offenders("from quest_ai_runner.core import x") == {"quest_ai_runner"}
    assert offenders("import json, esoi.runtime\nfrom . import registry\nfrom hubofhubs import a") == set()
    assert offenders("def f():\n    import pandas") == {"pandas"}  # function-level imports count too
    assert offenders("def f():\n    import httpx") == set()        # an extra's library, imported lazily
    assert offenders("import httpx") == {"httpx"}                     # but never at module level
    assert offenders("try:\n    import pypdf\nexcept ImportError:\n    pass") == {"pypdf"}
    assert offenders("import textual\nimport pydantic", vendor=True) == set()     # a vendor folder may import the libraries of the extra that carries it
    assert offenders("import requests", vendor=True) == {"requests"}              # and nothing else
    assert offenders("import pydantic") == {"pydantic"}                           # the hub's own code never imports them at module level
