"""The corpus an arm retrieves from: files cut at natural boundaries into units, with the descriptors, links and history priors an arm may use.

Everything here is extractive and deterministic (no model): a Python file is cut with ``ast`` into a header unit (module docstring and
imports) and one unit per top-level function or class, a long class is cut again at its methods, and any other text is cut at blank lines
and headings. Each unit carries three fields (``path``: the file's path and its generated descriptor, ``title``: the unit's own names and
docstring, ``body``: its text), so an index can weigh a match in a title above one in a body.
"""
from __future__ import annotations

import ast
import hashlib
import math
import posixpath
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

CHARS_PER_TOKEN = 4
MAX_UNIT_CHARS = 2400
STOP = frozenset("a an and are as at be by for from has have how i in is it of on or that the this to was what when where which who why with do does did "
                 "not can will should would into out up all any more also self none true false return def class import if else elif then use used using".split())
WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")
CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def stem(word: str) -> str:
    """A light suffix stripper (plural, past tense and gerund), enough to join ``retries`` and ``retry`` without a library."""
    for suffix, keep in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3 and not (suffix == "s" and word.endswith("ss")):
            return word[:-len(suffix)] + keep
    return word


def tokens(text: str) -> List[str]:
    """Lower-case terms of ``text``: each identifier whole and split at underscores and camel humps, stemmed, stop words dropped."""
    out: List[str] = []
    for raw in WORD.findall(text or ""):
        parts = [p.lower() for piece in raw.split("_") if piece for p in CAMEL.findall(piece)]
        words = [raw.lower()] if len(parts) > 1 else []
        words += parts
        out += [stem(w) for w in words if len(w) > 1 and w not in STOP]
    return out


def tokens_of(text: str) -> int:
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


@dataclass
class Unit:
    index: int
    id: str
    file: str
    text: str
    start: int
    title: str = ""
    header: bool = False
    tokens: int = 0
    fields: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class Corpus:
    files: Dict[str, str]
    units: List[Unit]
    by_file: Dict[str, List[int]]
    links: Dict[str, Set[str]]
    cochange: Dict[str, Counter]
    recency: Dict[str, float]
    descriptors: Dict[str, str]
    digest: str
    size_bytes: int = 0
    history: List[Mapping[str, object]] = field(default_factory=list)

    def neighbours(self, path: str) -> Set[str]:
        return self.links.get(path, set())


# ---- cutting -----------------------------------------------------------------------------------------------------------------

def split_text(text: str, limit: int = MAX_UNIT_CHARS) -> List[Tuple[int, str]]:
    """Cut prose or config at blank lines and headings into pieces of about ``limit`` characters: ``(first line number, text)``."""
    pieces: List[Tuple[int, str]] = []
    current: List[str] = []
    start, size = 1, 0
    for number, line in enumerate(text.splitlines(), 1):
        boundary = (not line.strip() or line.startswith("#")) and size >= limit // 2
        if boundary or size + len(line) > limit:
            if current:
                pieces.append((start, "\n".join(current)))
            current, start, size = [], number, 0
        current.append(line)
        size += len(line) + 1
    if current:
        pieces.append((start, "\n".join(current)))
    return pieces or [(1, text)]


def python_pieces(text: str, limit: int = MAX_UNIT_CHARS) -> List[Tuple[int, str, str, bool]]:
    """``(line, text, title, is_header)`` for a Python source: the header, then each top-level definition (a long class by method)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [(n, t, "", n == 1) for n, t in split_text(text, limit)]
    lines = text.splitlines()

    def cut(node: ast.AST) -> Tuple[int, int]:
        first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        return first, node.end_lineno or node.lineno

    def title_of(node: ast.AST, prefix: str = "") -> str:
        doc = (ast.get_docstring(node) or "").split("\n\n")[0].replace("\n", " ")
        return f"{prefix}{node.name} {doc}".strip()

    pieces: List[Tuple[int, str, str, bool]] = []
    body = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    header_end = (cut(body[0])[0] - 1) if body else len(lines)
    module_doc = (ast.get_docstring(tree) or "").split("\n\n")[0].replace("\n", " ")
    pieces.append((1, "\n".join(lines[:header_end])[:limit * 2], module_doc, True))
    for node in body:
        first, last = cut(node)
        chunk = "\n".join(lines[first - 1:last])
        if len(chunk) > limit and isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if methods:
                head_end = cut(methods[0])[0] - 1
                pieces.append((first, "\n".join(lines[first - 1:head_end]), title_of(node), False))
                for method in methods:
                    a, b = cut(method)
                    pieces.append((a, "\n".join(lines[a - 1:b])[:limit * 2], title_of(method, node.name + "."), False))
                continue
        pieces.append((first, chunk[:limit * 2] if len(chunk) > limit * 2 else chunk, title_of(node), False))
    return pieces


def cut_file(path: str, text: str, unit: str) -> List[Tuple[int, str, str, bool]]:
    if unit == "file":
        return [(1, text, "", True)]
    if path.endswith(".py"):
        return python_pieces(text)
    return [(n, t, t.splitlines()[0].lstrip("# ") if t else "", n == 1) for n, t in split_text(text)]


# ---- links, history and descriptors ------------------------------------------------------------------------------------------

def python_imports(path: str, text: str, known: Set[str]) -> Set[str]:
    """The corpus files a Python file imports (absolute and relative imports resolved against ``known``)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    here = posixpath.dirname(path).split("/") if posixpath.dirname(path) else []
    found: Set[str] = set()

    def add(parts: Sequence[str]) -> None:
        base = "/".join(parts)
        for candidate in (base + ".py", base + "/__init__.py"):
            if candidate in known:
                found.add(candidate)
                return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                add(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            module = node.module.split(".") if node.module else []
            base = module if not node.level else here[:len(here) - (node.level - 1)] + module
            add(base)
            for alias in node.names:
                add(base + [alias.name])
    found.discard(path)
    return found


def import_links(files: Mapping[str, str]) -> Dict[str, Set[str]]:
    """Import links in both directions: a file's neighbours are the files it imports and the files that import it."""
    known = set(files)
    links: Dict[str, Set[str]] = defaultdict(set)
    for path, text in files.items():
        if path.endswith(".py"):
            for target in python_imports(path, text, known):
                links[path].add(target)
                links[target].add(path)
    return dict(links)


def cochange_counts(history: Iterable[Mapping[str, object]], known: Set[str]) -> Dict[str, Counter]:
    """For each file, how often each other file changed in the same commit (a commit's weight is shared among its pairs)."""
    counts: Dict[str, Counter] = defaultdict(Counter)
    for commit in history:
        changed = [f for f in commit.get("files", []) if f in known]
        for a in changed:
            for b in changed:
                if a != b:
                    counts[a][b] += 1.0 / max(len(changed) - 1, 1)
    return dict(counts)


def recency_of(history: Sequence[Mapping[str, object]], known: Set[str]) -> Dict[str, float]:
    """1 for the file changed in the newest commit, falling to 0 for the oldest, by position in the history; absent from history is 0."""
    ordered = sorted(history, key=lambda c: str(c.get("date", "")))
    last: Dict[str, int] = {}
    for position, commit in enumerate(ordered):
        for f in commit.get("files", []):
            if f in known:
                last[f] = position
    top = max(len(ordered) - 1, 1)
    return {f: (p / top) for f, p in last.items()}


def describe(path: str, text: str, idf: Mapping[str, float], linked: Iterable[str], top: int = 8) -> str:
    """The generated descriptor of a file: its path words, headings, names, the words that set it apart from the corpus and what it is linked to."""
    heads = re.findall(r"^#{1,3}\s+(.+)$", text, flags=re.M)[:6]
    names: List[str] = []
    if path.endswith(".py"):
        try:
            tree = ast.parse(text)
            names = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))][:30]
            doc = (ast.get_docstring(tree) or "").split("\n\n")[0].replace("\n", " ")
            heads = [doc] + heads if doc else heads
        except SyntaxError:
            pass
    counts = Counter(tokens(text))
    scored = sorted(counts, key=lambda w: -(counts[w] * idf.get(w, 0.0)))[:top]
    return " ".join([path.replace("/", " ")] + heads + names + scored + [posixpath.splitext(posixpath.basename(l))[0] for l in sorted(linked)][:12])


def digest_of(files: Mapping[str, str], history: Sequence[Mapping[str, object]], unit: str) -> str:
    h = hashlib.sha256(unit.encode())
    for path in sorted(files):
        h.update(path.encode())
        h.update(hashlib.sha256(files[path].encode()).digest())
    for commit in history:
        h.update(str(commit.get("commit", commit.get("subject", ""))).encode())
    return h.hexdigest()[:16]


def build_corpus(files: Mapping[str, str], history: Sequence[Mapping[str, object]] = (), unit: str = "chunk") -> Corpus:
    """Cut ``files`` into units and attach the links and priors. ``unit`` is ``chunk`` (natural boundaries) or ``file`` (whole files)."""
    known = set(files)
    links = import_links(files)
    df: Counter = Counter()
    for text in files.values():
        df.update(set(tokens(text)))
    total = max(len(files), 1)
    idf = {w: math.log(1 + total / c) for w, c in df.items()}
    descriptors = {p: describe(p, t, idf, links.get(p, ())) for p, t in files.items()}
    units: List[Unit] = []
    by_file: Dict[str, List[int]] = defaultdict(list)
    for path in sorted(files):
        for start, text, title, header in cut_file(path, files[path], unit):
            u = Unit(index=len(units), id=f"{path}:{start}", file=path, text=text, start=start, title=title, header=header,
                     tokens=tokens_of(text))
            u.fields = {"path": tokens(descriptors[path]), "title": tokens(f"{path} {title}" if title else path), "body": tokens(text)}
            units.append(u)
            by_file[path].append(u.index)
    return Corpus(files=dict(files), units=units, by_file=dict(by_file), links=links, cochange=cochange_counts(history, known),
                  recency=recency_of(history, known), descriptors=descriptors, digest=digest_of(files, history, unit),
                  size_bytes=sum(len(t.encode()) for t in files.values()), history=list(history))


def cached_corpus(files: Mapping[str, str], history: Sequence[Mapping[str, object]] = (), unit: str = "chunk", folder: Optional[str] = None) -> Corpus:
    """``build_corpus`` kept on disk by the digest of its inputs, so a rerun over the same files and history skips the cutting and tokenizing."""
    import pickle
    import tempfile
    from pathlib import Path
    digest = digest_of(files, history, unit)
    path = Path(folder or Path(tempfile.gettempdir()) / "hubofhubs_retrieval") / f"corpus_{digest}.pkl"
    if path.is_file():
        try:
            return pickle.loads(path.read_bytes())
        except Exception:  # noqa: BLE001  an unreadable cache is rebuilt
            pass
    corpus = build_corpus(files, history, unit)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(corpus))
    return corpus
