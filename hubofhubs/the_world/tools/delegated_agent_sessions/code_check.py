"""The hub's code check of written text after a session: what code alone can say about the files a session wrote, with no model.

Role: after a session reports, the hub reads the prose files it wrote and lists what it cannot account for: a figure no source file holds, and a file the text names that
cannot be found. A finding is only worth a resumed turn when the check can substantiate it, so the check looks where the goal and the text point before it calls a file
missing (a base folder either names, an absolute folder the goal names, the end of a path under a parent), counts the digits of a file name as no claim, and reports a total
or count that shows no working as ``could not be verified`` (a person or a reviewer decides) rather than as certainly absent. ``native_runner.worth_resuming`` resumes a
session only for the findings that are certain. Standard library only; the folder walk and the text reader are the text loop's (``solution_loop``), imported when the check runs."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Collection, List, Sequence

NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
CITED_FILE = re.compile(r"(?<![\w/.-])[\w./-]*\w\.(?:md|txt|csv|json|yaml|yml|rst|py)(?![\w])")
NOT_IN_FOLDER = "is not in the folder"
NO_SOURCE = "is in no source file"
COULD_NOT_VERIFY = "could not be verified"
ABSOLUTE_PATH = re.compile(r"(?<![\w.:/~-])/(?:[\w.@+-]+/)*[\w.@+-]+")
AGGREGATE_CUES = ("total", "sum ", "sums", "summed", "count", "number of", "overall", "average", "mean", "aggregate", "altogether", "combined", "computed", "calculated",
                  "all together", "in all", "across")
ASKED_CUES = ("how many", "how much", "convert", "percent", "difference", "largest", "smallest", "most ", "least ", "per ", "rate", "latest", "current", "tally")
WORKING_MARKS = ("=", "+", "×", "*", " x ", " plus ", " times ", "sum of", "summed", "adds up")


def figures(text: str) -> List[str]:
    """The numbers of two digits or more in ``text``, without thousands separators or a trailing ``.0``."""
    out = []
    for raw in NUMBER.findall(text):
        value = raw.replace(",", "").rstrip(".")
        if sum(ch.isdigit() for ch in value) >= 2:
            out.append(value)
    return out


def derived(known: Sequence[str], limit: int = 150) -> set:
    """The sums, differences and products of each pair of source figures (the first ``limit`` of them): a figure worked out from two figures the
    sources hold is supported by them, so the code check does not list it."""
    values = []
    for text in sorted(known)[:limit]:
        try:
            values.append(float(text))
        except ValueError:
            continue
    out = set()
    for a in values:
        for b in values:
            for result in (a + b, a - b, a * b):
                if result > 0:
                    out.add(str(int(result)) if float(result).is_integer() else f"{result:.2f}".rstrip("0").rstrip("."))
    return out


def folders_of(paths: Sequence[str]) -> set:
    """Every folder (relative path) that holds a file, the nested ones included."""
    out = set()
    for rel in paths:
        parts = rel.split("/")[:-1]
        out |= {"/".join(parts[:n]) for n in range(1, len(parts) + 1)}
    return out


def named_in(folder: str, text: str) -> bool:
    """Whether ``text`` names ``folder``, as its whole relative path or as its own name, as a word and not inside another name."""
    for term in {folder, folder.rsplit("/", 1)[-1]}:
        if term and re.search(r"(?<![\w.-])" + re.escape(term) + r"(?![\w-])", text):
            return True
    return False


def roots_named(text: str) -> List[str]:
    """The existing folders ``text`` names by an absolute path: other places the session was given to read."""
    out: List[str] = []
    for found in ABSOLUTE_PATH.findall(text or ""):
        found = found.rstrip(".,;:)")
        if os.path.isdir(found) and found not in out:
            out.append(found)
    return out


def resolves(name: str, paths: set, names: set, bases: Sequence[str], roots: Sequence[str]) -> bool:
    """Whether a file a text names exists where the work can reach it: in the working folder (as written, by its own name, or as the end of the path), under a folder the
    goal or the text itself names as the place paths are relative to, as an absolute path, or under another root the session was given."""
    plain = name.lstrip("./") if not name.startswith("/") else name
    if name in names or plain in names:
        return True
    if name.startswith("/") and os.path.isfile(name):
        return True
    parts = plain.split("/")
    if any("/".join(parts[n:]) in paths for n in range(1, len(parts))):          # relative to a folder above the one the working folder holds
        return True
    if any(f"{base}/{plain}" in paths for base in bases):
        return True
    return any(os.path.isfile(os.path.join(r, plain)) for r in roots)


def shows_working(lines: Sequence[str], at: int) -> bool:
    """Whether the paragraph around line ``at`` of a written text shows the arithmetic behind a figure: at least two other figures and a mark of calculation."""
    start, end = at, at
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    paragraph = "\n".join(lines[start:end + 1])
    return len(figures(paragraph)) >= 3 and any(mark in paragraph.lower() for mark in WORKING_MARKS)


def unsupported(root: str, changed: Sequence[str], limit: int = 20, skip: Collection[str] = (), goal: str = "", roots: Sequence[str] = ()) -> List[str]:
    """What code alone can tell about written text, with no model. Each figure in a changed prose file that appears in no other file of the folder and is not an
    aggregate the text shows its working for (``... is in no source file``, or ``... could not be verified`` when the goal asks for something worked out or the line says it is
    a total or count, which code cannot check and a person or a reviewer can), and each file it names that cannot be found. A file is found in the working folder, under a folder
    the goal or the text names, or under another root the goal names by an absolute path or the caller gives (``roots``), before it is called missing. A figure worked out
    from two source figures is not listed."""
    from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import prose, read_text, walk
    written = {rel: read_text(Path(root) / rel) or "" for rel in changed if prose(rel)}
    if not written:
        return []
    paths = [rel for rel, _, _ in walk(root, skip=skip)]
    sources = " ".join(read_text(Path(root) / rel) or "" for rel in paths if rel not in changed)
    known = set(figures(sources))
    known |= derived(known)
    pathset = set(paths)
    names = pathset | {rel.rsplit("/", 1)[-1] for rel in paths}
    folders = folders_of(paths)
    computes = any(cue in (goal or "").lower() for cue in AGGREGATE_CUES + ASKED_CUES)       # the goal asks for something worked out: a figure not in a source is then not a finding
    found: List[str] = []
    for rel, text in written.items():
        lines = text.splitlines()
        base_text = (goal or "") + "\n" + text
        bases = [d for d in sorted(folders) if named_in(d, base_text)]
        other = list(roots) + [r for r in roots_named(base_text) if r not in roots]
        seen_figures = set()
        for at, line in enumerate(lines):
            for value in figures(CITED_FILE.sub(" ", ABSOLUTE_PATH.sub(" ", line))):          # the digits of a file name or a path are not a claim
                if value in known or value in seen_figures:
                    continue
                seen_figures.add(value)
                if shows_working(lines, at):
                    continue
                if computes or any(cue in line.lower() for cue in AGGREGATE_CUES):
                    found.append(f"{rel}: the figure {value} {COULD_NOT_VERIFY} (a total or count: show how it is computed from the sources)")
                else:
                    found.append(f"{rel}: the figure {value} {NO_SOURCE}")
        for name in dict.fromkeys(CITED_FILE.findall(text)):
            if not name.startswith(("-", "*")) and not resolves(name, pathset, names, bases, other):       # the end of a pattern such as ``*-tally.md`` is not a file
                found.append(f"{rel}: names the file {name}, which {NOT_IN_FOLDER}")
    return found[:limit]
