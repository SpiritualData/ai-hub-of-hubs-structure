"""The pinned corpus of the cards-from-files component: the files a builder is handed, the cases, and the fixed selector's package.

``datasets/qar_pin.json`` names the Quest AI Runner commit and the hub commit the corpus is read from, and holds two digests: the
sha256 of ``evaluation/components/context_selection/cases.json`` at the QAR commit, and the sha256 of the sorted file list of the
corpus walk. Everything is read with ``git archive`` and ``git show`` into a cached temporary folder, so no working tree is read or
touched, and the pins are checked every time the corpus is used: a mismatch is a ``PinMismatch``, never a quiet re-score.

The corpus is every ``.py`` file of QAR at its commit (the ``evaluation`` folder left out, as QAR's own context-selection component
leaves it out) followed by the ``.py`` files of the ``hubofhubs`` package at the hub commit, in walk order. Four of the 63 targets
are hub files.

The checkouts are found, in order, from ``CARDS_FROM_FILES_QAR_REPO`` and ``CARDS_FROM_FILES_HUB_REPO`` (git working copies),
then the sibling folder ``quest-ai-runner`` of this repository, then (QAR only) a clone of the pinned ``qar_repository`` URL.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
HUB_ROOT = HERE.parents[1]
PIN_FILE = HERE / "datasets" / "qar_pin.json"
CASES_AT_COMMIT = "evaluation/components/context_selection/cases.json"
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".quest-context", ".eggs", ".mypy_cache",
             ".pytest_cache", "dist", "build", "quest_ai_runner.egg-info"}
SKIP_TOP_LEVEL = {"evaluation"}
HUB_PACKAGE = "hubofhubs"


class PinMismatch(RuntimeError):
    """The corpus or the cases are not the ones the pin file names."""


class PinUnavailable(RuntimeError):
    """A pinned commit cannot be read here (no checkout holds it); the message says how to supply one."""


@dataclass
class Corpus:
    root: Path             # the folder builders are handed: root-relative paths of every file in ``files``
    selector_path: Path    # a folder holding the ``quest_ai_runner`` package at the pinned commit, for the fixed selector
    files: List[str]       # walk order
    cases: List[dict]


def read_pin() -> dict:
    return json.loads(PIN_FILE.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def files_digest(files) -> str:
    """The sha256 of the sorted file list, one path per line."""
    return sha256_text("\n".join(sorted(files)))


def run_git(repo: Path, *args: str, check: bool = True) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if check and done.returncode:
        raise PinUnavailable(f"git {' '.join(args)} failed in {repo}: {done.stderr.decode(errors='replace').strip()[:200]}")
    return done.stdout


def has_commit(repo: Path, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode == 0


def checkout_with(commit: str, candidates) -> Path | None:
    return next((Path(c) for c in candidates if c and Path(c).is_dir() and has_commit(Path(c), commit)), None)


def qar_repo(pin: dict, cache: Path) -> Path:
    found = checkout_with(pin["qar_commit"], [os.environ.get("CARDS_FROM_FILES_QAR_REPO"), HUB_ROOT.parent / "quest-ai-runner"])
    if found:
        return found
    clone = cache / "qar_clone"
    if not clone.is_dir():
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", pin["qar_repository"], str(clone)], check=True, capture_output=True)
    if not has_commit(clone, pin["qar_commit"]):
        raise PinUnavailable(f"commit {pin['qar_commit']} is not in {pin['qar_repository']}; set CARDS_FROM_FILES_QAR_REPO to a checkout that has it")
    return clone


def hub_repo(pin: dict) -> Path:
    found = checkout_with(pin["hub_commit"], [os.environ.get("CARDS_FROM_FILES_HUB_REPO"), HUB_ROOT])
    if not found:
        raise PinUnavailable(f"hub commit {pin['hub_commit']} is not in this repository; set CARDS_FROM_FILES_HUB_REPO to a checkout that has it")
    return found


def walk_py(base: Path, prefix: str = "", skip_top: frozenset = frozenset()) -> List[str]:
    """Sorted ``.py`` paths under ``base`` (``prefix`` put in front), directories in sorted order, a folder's files before its subfolders."""
    found = []
    for dirpath, dirnames, filenames in os.walk(base):
        top = Path(dirpath) == base
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not (top and d in skip_top))
        for name in sorted(filenames):
            if name.endswith(".py"):
                found.append(str(Path(prefix) / (Path(dirpath) / name).relative_to(base)))
    return found


def corpus_files(root: Path) -> List[str]:
    return walk_py(root, skip_top=frozenset(SKIP_TOP_LEVEL | {HUB_PACKAGE})) + walk_py(root / HUB_PACKAGE, HUB_PACKAGE)


def archive_into(repo: Path, commit: str, pathspecs: List[str], target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    produced = subprocess.run(["git", "-C", str(repo), "archive", commit, "--", *pathspecs], capture_output=True)
    if produced.returncode:
        raise PinUnavailable(f"git archive {commit} failed in {repo}: {produced.stderr.decode(errors='replace').strip()[:200]}")
    subprocess.run(["tar", "-x", "-C", str(target)], input=produced.stdout, check=True)


def cases_at_pin(pin: dict, qar: Path) -> List[dict]:
    raw = run_git(qar, "show", f"{pin['qar_commit']}:{CASES_AT_COMMIT}").decode("utf-8")
    if sha256_text(raw) != pin["cases_sha256"]:
        raise PinMismatch(f"cases.json at {pin['qar_commit']} has sha256 {sha256_text(raw)}, the pin names {pin['cases_sha256']}")
    return json.loads(raw)


def check_files(files: List[str], pin: dict) -> None:
    if files_digest(files) != pin["files_sha256"]:
        raise PinMismatch(f"the corpus walk has sha256 {files_digest(files)} over {len(files)} files, the pin names {pin['files_sha256']}")


def build_into(target: Path, pin: dict, qar: Path, hub: Path) -> None:
    archive_into(qar, pin["qar_commit"], ["*.py"], target / "corpus")
    shutil.rmtree(target / "corpus" / "evaluation", ignore_errors=True)
    archive_into(hub, pin["hub_commit"], [f"{HUB_PACKAGE}/*.py"], target / "corpus")
    (target / "selector").mkdir()
    shutil.copytree(target / "corpus" / "quest_ai_runner", target / "selector" / "quest_ai_runner")


def cache_root() -> Path:
    return Path(os.environ.get("CARDS_FROM_FILES_CACHE") or Path(tempfile.gettempdir()) / "hubofhubs_cards_from_files")


_LOADED: dict = {}


def load() -> Corpus:
    """The verified corpus, materialised once per process (and once per machine in the cache folder)."""
    pin = read_pin()
    key = json.dumps(pin, sort_keys=True)
    if key in _LOADED:
        return _LOADED[key]
    cache = cache_root()
    qar = qar_repo(pin, cache)
    cases = cases_at_pin(pin, qar)
    target = cache / f"{pin['qar_commit']}_{pin['hub_commit']}"
    if not (target / "ready").is_file():
        cache.mkdir(parents=True, exist_ok=True)
        building = Path(tempfile.mkdtemp(prefix="building_", dir=cache))
        try:
            build_into(building, pin, qar, hub_repo(pin))
            (building / "ready").write_text("ok\n")
            shutil.rmtree(target, ignore_errors=True)
            building.rename(target)
        finally:
            shutil.rmtree(building, ignore_errors=True)
    files = corpus_files(target / "corpus")
    check_files(files, pin)
    _LOADED[key] = Corpus(root=target / "corpus", selector_path=target / "selector", files=files, cases=cases)
    return _LOADED[key]
