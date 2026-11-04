"""Public Python repositories for the ``topic_open`` and ``grouping`` kinds of ``context_retrieval``.

Three permissively licensed repositories (BSD-3-Clause) are read with ``git archive`` at the pinned commits of ``datasets/open_code/pin.json`` into
the cache folder, never vendored: a library and the libraries around it, so a request made while working in one may need a file of another. The
corpus is every ``.py`` file of each repository's package and ``tests`` folder, a file's path prefixed with the repository's name. The pin holds each
repository's URL, commit, licence and the sha256 of its licence file, and the sha256 of the sorted file list; ``datasets/open_code/cases.json`` and
``history.json`` carry their own sha256 in the pin. Every pin is checked on every use (a mismatch is ``PinMismatch``).

The cases are built the way ``cards_from_files.topic_cases`` builds them: a commit that changed two to eight package files whose subject (the
trailing ``(#123)`` removed) reads as a topic and names no file or identifier is a request; the files it changed are the needed set. The newest
``TOTAL`` such commits across the repositories are the cases, every older commit (either repository) is the history an arm may learn from, so the
split in time is global. A fixed hash of the case id sends ``GROUPING`` of them to the ``grouping`` kind, whose request is made while working in the
repository's sibling (``SIBLING``): its focus is the sibling, its needed files are at home elsewhere.

    python3 evaluation/context_retrieval/open_code.py   # regenerate on purpose: refuses to replace a pinned file without --replace
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cards_from_files import corpus as base  # noqa: E402
from cards_from_files import topic_cases  # noqa: E402

HERE = Path(__file__).resolve().parent / "datasets" / "open_code"
PIN_FILE, CASES_FILE, HISTORY_FILE = HERE / "pin.json", HERE / "cases.json", HERE / "history.json"
REPOS = {   # name: (url, package folder)
    "httpx": ("https://github.com/encode/httpx", "httpx"),
    "httpcore": ("https://github.com/encode/httpcore", "httpcore"),
    "starlette": ("https://github.com/encode/starlette", "starlette"),
}
SIBLING = {"httpx": "httpcore", "httpcore": "httpx", "starlette": "httpx"}   # the focus of a grouping request made about a repository's commit
TOTAL, GROUPING = 95, 32
MIN_CHANGED, MAX_CHANGED, MIN_SUBJECT = 2, 8, 30
NOT_A_TOPIC = re.compile(r"\b(bumps?|versions?|release|merge|revert|dependabot|deps)\b", re.I)
PR_SUFFIX = re.compile(r"\s*\(#\d+\)\s*$")


class PinMismatch(base.PinMismatch):
    """A repository, its licence, the corpus or a case file is not the one the pin names."""


def tag(name: str) -> str:
    return f"repo:{name}"


def checkout(name: str, pin: dict) -> Path:
    """A git checkout holding the pinned commit: ``OPEN_CODE_<NAME>_REPO``, else a clone of the pinned URL in the cache folder."""
    wanted = pin["repos"][name]
    given = os.environ.get(f"OPEN_CODE_{name.upper()}_REPO")
    if given and Path(given).is_dir() and base.has_commit(Path(given), wanted["commit"]):
        return Path(given)
    clone = base.cache_root() / "open_code_clones" / name
    if not clone.is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", wanted["url"], str(clone)], check=True, capture_output=True)
    if not base.has_commit(clone, wanted["commit"]):
        raise base.PinUnavailable(f"commit {wanted['commit']} is not in {wanted['url']}; set OPEN_CODE_{name.upper()}_REPO to a checkout that has it")
    return clone


def licence_of(repo: Path, commit: str, file: str) -> str:
    return base.run_git(repo, "show", f"{commit}:{file}").decode("utf-8")


def read_pin() -> dict:
    return json.loads(PIN_FILE.read_text(encoding="utf-8"))


def archive(name: str, pin: dict, target: Path) -> None:
    wanted = pin["repos"][name]
    repo = checkout(name, pin)
    text = licence_of(repo, wanted["commit"], wanted["licence_file"])
    if base.sha256_text(text) != wanted["licence_sha256"]:
        raise PinMismatch(f"{name}: the licence file has sha256 {base.sha256_text(text)}, the pin names {wanted['licence_sha256']}")
    base.archive_into(repo, wanted["commit"], [f"{wanted['package']}/*.py", "tests/*.py"], target / name)


def corpus_files(root: Path) -> List[str]:
    return [p for name in REPOS for p in base.walk_py(root / name, name)]


_LOADED: dict = {}


def load() -> dict:
    """``{root, files (path to text), history, meta}`` of the verified corpus, cached once per process and once per machine."""
    pin = read_pin()
    key = json.dumps(pin, sort_keys=True)
    if key in _LOADED:
        return _LOADED[key]
    target = base.cache_root() / ("open_code_" + hashlib.sha256(key.encode()).hexdigest()[:12])
    if not (target / "ready").is_file():
        building = Path(tempfile.mkdtemp(prefix="building_", dir=base.cache_root() if base.cache_root().is_dir() else None))
        try:
            for name in REPOS:
                archive(name, pin, building / "corpus")
            (building / "ready").write_text("ok\n")
            shutil.rmtree(target, ignore_errors=True)
            building.rename(target)
        finally:
            shutil.rmtree(building, ignore_errors=True)
    root = target / "corpus"
    files = corpus_files(root)
    if base.files_digest(files) != pin["files_sha256"]:
        raise PinMismatch(f"the corpus walk has sha256 {base.files_digest(files)} over {len(files)} files, the pin names {pin['files_sha256']}")
    texts = {f: (root / f).read_text(encoding="utf-8", errors="replace") for f in files}
    history = checked(HISTORY_FILE, "history_sha256", "commits")
    _LOADED[key] = dict(root=root, files=texts, history=history, meta=metadata(texts, history))
    return _LOADED[key]


def metadata(files: Dict[str, str], history: List[dict]) -> Dict[str, dict]:
    """Item metadata that is free: kind ``file``, its home repository, and the date of the last commit of the history that changed it (a file
    no commit of the history changed has none: a date after the history would tell an arm about the future)."""
    last: Dict[str, str] = {}
    for commit in sorted(history, key=lambda c: c["date"]):
        for f in commit["files"]:
            last[f] = commit["date"]
    meta = {}
    for path in files:
        entry = dict(kind="file", affinity_tags=[tag(path.split("/", 1)[0])])
        if path in last:
            entry["timestamp"] = last[path]
        meta[path] = entry
    return meta


def checked(path: Path, pin_key: str, key: str) -> list:
    text = path.read_text(encoding="utf-8")
    if base.sha256_text(text) != read_pin()[pin_key]:
        raise PinMismatch(f"{path.name} has sha256 {base.sha256_text(text)}, the pin names {read_pin()[pin_key]}")
    return json.loads(text)[key]


def place(case_id: str) -> int:
    return int(hashlib.sha256(case_id.encode()).hexdigest(), 16)


def cases() -> Dict[str, List[dict]]:
    """``{"topic_open": [...], "grouping": [...]}`` from the committed, checked case file."""
    out: Dict[str, List[dict]] = {"topic_open": [], "grouping": []}
    for case in checked(CASES_FILE, "cases_sha256", "cases"):
        out[case["kind"]].append(dict(case))
    return out


def qualifies(entry: dict, package: str) -> bool:
    subject = PR_SUFFIX.sub("", entry["subject"]).strip()
    changed = [f for f in entry["files"] if f.startswith(package + "/") and f.endswith(".py")]
    return (MIN_CHANGED <= len(changed) <= MAX_CHANGED and len(subject) >= MIN_SUBJECT and not topic_cases.names_something(subject)
            and not NOT_A_TOPIC.search(subject))


def write(commits: Dict[str, str], replace: bool = False) -> dict:
    """Derive cases and history from checkouts at the given commits and write the three files and the pin; refuses to replace a pin."""
    if PIN_FILE.exists() and not replace:
        raise base.PinMismatch(f"{PIN_FILE.name} exists: the cases are pinned (pass --replace to replace them on purpose)")
    pin = dict(repos={n: dict(url=REPOS[n][0], commit=commits[n], package=REPOS[n][1], licence="BSD-3-Clause", licence_file="LICENSE.md") for n in REPOS})
    entries, everything, texts = [], [], {}
    for name in REPOS:
        repo = checkout(name, pin)
        pin["repos"][name]["licence_sha256"] = base.sha256_text(licence_of(repo, commits[name], "LICENSE.md"))
        archive(name, pin, base.cache_root() / "open_code_generating")
    root = base.cache_root() / "open_code_generating"
    files = corpus_files(root)
    known = set(files)
    for name in REPOS:
        for entry in topic_cases.history_of(checkout(name, pin), commits[name]):
            entry["repo"] = name
            entry["files_all"] = [f"{name}/{f}" for f in entry["files"]]
            entry["files"] = [f for f in entry["files_all"] if f in known]
            everything.append(entry)
            if qualifies(dict(entry, files=[f[len(name) + 1:] for f in entry["files"]]), REPOS[name][1]):
                needed = [f for f in entry["files"] if f.startswith(f"{name}/{REPOS[name][1]}/")]
                if len(needed) >= MIN_CHANGED:
                    entries.append(dict(entry, needed=sorted(needed)))
    entries.sort(key=lambda e: (e["date"], e["commit"]), reverse=True)
    chosen = entries[:TOTAL]
    cut = chosen[-1]["date"]
    ids = [f"{e['repo']}-{e['commit'][:8]}" for e in chosen]
    grouping = set(sorted(ids, key=place)[:GROUPING])
    rows = []
    for e, ident in zip(chosen, ids):
        focus = SIBLING[e["repo"]] if ident in grouping else e["repo"]
        rows.append(dict(id=("GR-" if ident in grouping else "OT-") + ident, kind="grouping" if ident in grouping else "topic_open",
                         task=PR_SUFFIX.sub("", e["subject"]).strip(), needed=e["needed"], commit=e["commit"], date=e["date"], repo=e["repo"],
                         focus=[tag(focus)], timestamp=e["date"]))
    history = [dict(commit=e["commit"], date=e["date"], subject=PR_SUFFIX.sub("", e["subject"]).strip(), files=sorted(e["files"]))
               for e in everything if e["date"] < cut and MIN_CHANGED <= len(e["files"]) <= topic_cases.MAX_HISTORY_FILES]
    rule = ("the commit subject (trailing (#N) removed) is the task; it names no path, file, extension or identifier and is not a bump or release; "
            "the package files of the commit that are in the corpus are the needed set; history is every older commit of any repository")
    cases_text = json.dumps({"rule": rule, "cases": rows}, indent=1, ensure_ascii=False) + "\n"
    history_text = json.dumps({"rule": "every commit older than the oldest case, its files in the corpus", "commits": history}, indent=1, ensure_ascii=False) + "\n"
    CASES_FILE.write_text(cases_text, encoding="utf-8")
    HISTORY_FILE.write_text(history_text, encoding="utf-8")
    pin.update(files_sha256=base.files_digest(files), cases_sha256=base.sha256_text(cases_text), history_sha256=base.sha256_text(history_text),
               cases=len(rows), history_commits=len(history), oldest_case_date=cut, files=len(files))
    PIN_FILE.write_text(json.dumps(pin, indent=1) + "\n", encoding="utf-8")
    shutil.rmtree(root, ignore_errors=True)
    return pin


if __name__ == "__main__":
    given = {n: os.environ[f"OPEN_CODE_{n.upper()}_COMMIT"] for n in REPOS}
    print(write(given, replace="--replace" in sys.argv))
