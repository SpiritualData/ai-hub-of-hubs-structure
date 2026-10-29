"""Shared helpers for the resolution tests."""
import json
import subprocess
import sys
from pathlib import Path

import esoi

ROOT = Path(__file__).resolve().parent.parent
ESOI_PATH = str(Path(esoi.__file__).resolve().parent.parent)


def vendor(target: Path) -> Path:
    """Copy the package to ``target/site/hubofhubs``, outside any repository, as ``pip install --target`` would."""
    site = target / "site"
    site.mkdir(parents=True)
    import shutil
    shutil.copytree(ROOT / "hubofhubs", site / "hubofhubs", ignore=shutil.ignore_patterns("__pycache__"))
    return site


def run_vendored(site: Path, code: str, cwd: Path) -> dict:
    """Run ``code`` in a fresh interpreter whose only hub is the vendored copy; it prints one JSON object."""
    head = f"import sys; sys.path[:] = [{str(site)!r}, {ESOI_PATH!r}] + [p for p in sys.path if 'site-packages' not in p and p]\n"
    done = subprocess.run([sys.executable, "-c", head + code], cwd=cwd, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])
