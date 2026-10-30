"""The hub must not grow generic assembly again: that belongs in the esoi library (esoi docs: what-belongs-where.md)."""
import ast
from pathlib import Path

from esoi import assemble

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_FUNCTIONS = {name for name, obj in vars(assemble).items() if callable(obj) and not name.startswith("__")
                     and getattr(obj, "__module__", "") == assemble.__name__}
FORBIDDEN_FILES = {"assembly.py", "graph.py", "needs.py", "config.py"}   # the generic modules this one used to hold


def test_no_hub_module_defines_what_esoi_assemble_provides():
    clash = []
    for path in (ROOT / "hubofhubs").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in LIBRARY_FUNCTIONS:
                clash.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.name}")
    assert not clash, f"defined in esoi.assemble already; use it: {clash}"
    assert not FORBIDDEN_FILES & {p.name for p in (ROOT / "hubofhubs").iterdir()}


def test_no_hub_module_validates_names_or_walks_a_dependency_graph_itself():
    suspects = []
    for path in (ROOT / "hubofhubs").rglob("*.py"):
        text = path.read_text()
        if "[a-z0-9]" in text or "get_type_hints" in text or "find_spec" in text:
            suspects.append(path.name)
    assert not suspects, f"name patterns, constructor-type reading and module location are esoi.assemble's: {suspects}"
