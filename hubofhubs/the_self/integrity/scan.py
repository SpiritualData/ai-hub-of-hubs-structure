"""The static scan behind ``core_clean``. A VENDOR BRANCH is a decision in a consumer's core code made on a vendor's name: a
comparison (``==``, ``!=``, ``in``, ``is``) or a ``startswith`` / ``endswith`` call whose text includes a string constant that
holds one of the area's vendor terms as a whole word (``gemini`` in ``"gemini-3"`` counts, ``gemini`` inside another word does
not). Data tables, docstrings, log text and imports are not branches: a vendor name may sit in a table the registry reads,
which is exactly where it belongs. Lower is better; adapters and implementations are out of scope by design."""
import ast
import re
from pathlib import Path
from typing import Dict, List


def strings_in(node):
    return [c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and isinstance(c.value, str)]


def constants_of_branch(node):
    if isinstance(node, ast.Compare):
        return strings_in(node)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("startswith", "endswith"):
        return [s for arg in node.args for s in strings_in(arg)]
    return []


def scan_core(terms_by_area: Dict[str, List[str]], root: Path, relative_to: Path) -> Dict[str, List[str]]:
    """{area: ["relative/path.py:line: text", ...]} for every vendor branch under ``root``."""
    patterns = {area: re.compile(r"(?<![A-Za-z])(%s)(?![A-Za-z])" % "|".join(re.escape(t) for t in terms), re.I)
                for area, terms in terms_by_area.items() if terms}
    found = {area: [] for area in terms_by_area}
    for path in sorted(Path(root).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            for text in constants_of_branch(node):
                for area, rx in patterns.items():
                    if rx.search(text):
                        found[area].append(f"{path.relative_to(relative_to)}:{node.lineno}: {text[:40]}")
    return {area: sorted(set(v)) for area, v in found.items()}
