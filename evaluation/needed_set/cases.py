"""The cases of the needed-set component: topics taken from Quest AI Runner's git history, split in time.

A commit that changed two to eight Python files of the ``quest_ai_runner`` package is a task when its subject reads as a topic or
an intent and names nothing to look up: at least 30 characters and no path, file name, extension, code identifier or backticked text
(``names_something``, deterministic regular expressions). The subject is the request; the files the commit changed that exist in the
pinned corpus are the needed set (at least two).

The history is cut in time. The test cases are the ``SAMPLE_SIZE`` most recent such commits (git's own order). Every commit older than
the oldest test commit is the history a builder may learn from (``datasets/cochange_history.json``: for each, its subject and the
corpus files it changed); no test commit is in it. ``datasets/qar_commits.json`` holds the cases and ``datasets/qar_commits_pin.json``
the sha256 of both files, checked on every use. Nothing is regenerated silently: ``write`` refuses to replace a pinned file.
"""
from __future__ import annotations

import json
import posixpath
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

from cards_from_files import corpus as pinned

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "datasets" / "qar_commits.json"
HISTORY_FILE = HERE / "datasets" / "cochange_history.json"
PIN_FILE = HERE / "datasets" / "qar_commits_pin.json"
PACKAGE = "quest_ai_runner/"
MIN_CHANGED, MAX_CHANGED, MIN_SUBJECT, MIN_NEEDED, SAMPLE_SIZE = 2, 8, 30, 2, 150
MAX_HISTORY_FILES = 30   # a commit touching more files than this is a sweep, not a topic
GIT_ARGS = ("--no-merges", "--name-only", "--diff-filter=AM", "--format=COMMIT|%H|%cs|%s")
NAMES_SOMETHING = [re.compile(p) for p in (
    r"/",                                       # a path
    r"`",                                       # backticked text
    r"\.[A-Za-z]{1,5}\b",                       # a file name or extension (.py, .md, e.g)
    r"\b[A-Za-z0-9]+_[A-Za-z0-9_]+\b",          # snake_case
    r"\b[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*\b",     # CamelCase
    r"\b[a-z]+[A-Z][A-Za-z0-9]*\b",             # lowerCamelCase
    r"\w\(\)",                                  # a call: name()
)]


class CasesMismatch(RuntimeError):
    """The committed case or history file is not the one its pin names."""


def history_of(repo: Path, commit: str) -> List[dict]:
    """Every commit reachable from ``commit``, newest first: ``{commit, date, subject, files}`` (files added or modified)."""
    out = subprocess.run(["git", "-C", str(repo), "log", commit, *GIT_ARGS], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    commits: List[dict] = []
    for line in out.splitlines():
        if line.startswith("COMMIT|"):
            _, sha, date, subject = line.split("|", 3)
            commits.append(dict(commit=sha, date=date, subject=subject, files=[]))
        elif line.strip() and commits:
            commits[-1]["files"].append(line.strip())
    return commits


def names_something(subject: str) -> bool:
    """True when a subject carries a path, file name, extension, code identifier or backticked text."""
    return any(rule.search(subject) for rule in NAMES_SOMETHING)


def qualifies(entry: dict) -> bool:
    changed = [f for f in entry["files"] if f.startswith(PACKAGE) and f.endswith(".py")]
    return MIN_CHANGED <= len(changed) <= MAX_CHANGED and len(entry["subject"]) >= MIN_SUBJECT and not names_something(entry["subject"])


def derive(commits: List[dict], corpus_files, size: int = SAMPLE_SIZE) -> Tuple[List[dict], List[dict]]:
    """``(cases, history)``: the first ``size`` qualifying commits, newest first, that leave at least two changed files in the corpus,
    and the older commits (each ``{commit, date, subject, files}``, files in the corpus, 2 to ``MAX_HISTORY_FILES`` of them)."""
    known, cases, oldest = set(corpus_files), [], -1
    for position, entry in enumerate(commits):
        if not qualifies(entry):
            continue
        needed = sorted(f for f in entry["files"] if f.startswith(PACKAGE) and f.endswith(".py") and f in known)
        if len(needed) >= MIN_NEEDED:
            cases.append(dict(id=f"NS-{entry['commit'][:8]}", area=posixpath.dirname(needed[0]), task=entry["subject"], needed=needed,
                              commit=entry["commit"], date=entry["date"]))
            oldest = position
        if len(cases) == size:
            break
    history = []
    for entry in commits[oldest + 1:]:
        files = sorted(f for f in entry["files"] if f in known)
        if MIN_NEEDED <= len(files) <= MAX_HISTORY_FILES:
            history.append(dict(commit=entry["commit"], date=entry["date"], subject=entry["subject"], files=files))
    return cases, history


def document(rows: List[dict], pin: dict, key: str, rule: str) -> str:
    return json.dumps({"qar_commit": pin["qar_commit"], "rule": rule, key: rows}, indent=1, ensure_ascii=False) + "\n"


def write(replace: bool = False) -> dict:
    """Derive the cases and the older history from the sibling QAR checkout and write both files and their pin; refuses to replace a pin."""
    if PIN_FILE.exists() and not replace:
        raise CasesMismatch(f"{PIN_FILE.name} exists: the cases are pinned and are never regenerated silently (pass replace=True to replace them on purpose)")
    pin = pinned.read_pin()
    corpus = pinned.load()
    cases, history = derive(history_of(pinned.qar_repo(pin, pinned.cache_root()), pin["qar_commit"]), corpus.files)
    cases_text = document(cases, pin, "cases", "the commit subject is the task (it names no path, file, extension or identifier); "
                          "the quest_ai_runner files of the commit that are in the pinned corpus are the needed set")
    history_text = document(history, pin, "commits", "every commit older than the oldest test commit: its subject and the corpus files it changed; "
                            "no test commit is here")
    CASES_FILE.write_text(cases_text, encoding="utf-8")
    HISTORY_FILE.write_text(history_text, encoding="utf-8")
    record = dict(qar_commit=pin["qar_commit"], cases_file="datasets/qar_commits.json", cases_sha256=pinned.sha256_text(cases_text), cases=len(cases),
                  history_file="datasets/cochange_history.json", history_sha256=pinned.sha256_text(history_text), history_commits=len(history),
                  oldest_test_commit=cases[-1]["commit"],
                  sample=f"the {len(cases)} most recent topic-only qualifying commits with at least {MIN_NEEDED} files in the corpus")
    PIN_FILE.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def checked(path: Path, key: str) -> list:
    pin = json.loads(PIN_FILE.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    digest = pin["cases_sha256"] if key == "cases" else pin["history_sha256"]
    if pinned.sha256_text(text) != digest:
        raise CasesMismatch(f"{path.name} has sha256 {pinned.sha256_text(text)}, the pin names {digest}")
    return json.loads(text)[key]


def load() -> List[dict]:
    """The committed cases, after checking the file's sha256 against its pin and that every needed file is in the pinned corpus."""
    cases = checked(CASES_FILE, "cases")
    known = set(pinned.load().files)
    gone = sorted({f for c in cases for f in c["needed"] if f not in known})
    if gone or len(cases) != json.loads(PIN_FILE.read_text(encoding="utf-8"))["cases"]:
        raise CasesMismatch(f"the cases name {len(gone)} files that are not in the pinned corpus ({', '.join(gone[:3])}) or are not the pinned number")
    return cases


def load_history() -> List[dict]:
    """The commits older than every test case (sha256 checked against the pin): what a builder may learn co-change from."""
    return checked(HISTORY_FILE, "commits")


if __name__ == "__main__":
    import sys
    print(write(replace="--replace" in sys.argv))
