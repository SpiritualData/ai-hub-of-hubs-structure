"""Folder View arm ``evidence_ranked``: judge the folders by evidence, then rank the files by what the work itself points at. No model call.

1. ``judgment.scan`` leaves out dependency, build, cache, version-control, generated, binary and risky places by evidence in the folder, and says why.
2. Files the goal or context names come first; a name that points into a risky folder comes back flagged and is not shown unasked.
3. When what is left fits the budget, all of it is shown, best evidence first. Otherwise each file is scored on: words of the goal in its path, in its
   headings and in its opening (rare words count more, ``context_retriever.units`` tokens, fields weighted as ``lexical.FIELD_WEIGHTS``); the work's own
   entities (quoted strings, ids with digits, capitalised names) found in path or opening; a link from a named file (a path or file name it mentions, a
   Python import); the trail of files earlier runs used; and, when the goal asks for the latest, the newest of a numbered series.
4. Files whose evidence reaches ``BAR`` are shown best first until the fill is spent, at most ``MAX_PICKS``, so a corpus shows a few likely files and the model reads or searches for the rest.

The weights are fixed by reading before any arm was scored on ``evaluation/folder_view``. Standard library plus the hub."""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

from esoi import implementation

from hubofhubs.the_intelligence.subconscious.context_retriever.lexical import FIELD_WEIGHTS
from hubofhubs.the_intelligence.subconscious.context_retriever.units import python_imports, tokens
from hubofhubs.the_intelligence.subconscious.folder_view import judgment, named_folders, naming
from hubofhubs.the_intelligence.subconscious.folder_view.choice import FolderChoice, LeftOut, Pick

FILL = 24_000            # characters of likely files shown when the folder is too large to show whole
MAX_PICKS = 10           # at most this many unasked files for a folder that does not fit
BAR = 0.30               # the evidence a file needs to be shown unasked
ENTITY_WEIGHT = 0.5      # an entity of the work found in a file's path or opening
LINK_WEIGHT = 0.6        # a file a named file refers to
TRAIL_WEIGHT = 0.4       # a file earlier runs of this work used (and 0.2 more when one changed it)
RECENT_WEIGHT = 0.4      # the newest of a numbered series, when the goal asks for the latest
CONTEXT_SHARE = 0.25     # a word of the context counts this much beside a word of the goal
IGNORED = frozenset(tokens("find what say tell show list explain summarise summarize review check describe write make give does did decide decided point points details work continue time last understand look read open"))
FOLDER_BAR = 0.20        # a file inside a named folder needs less evidence of its own: the folder is already named
FOLDER_PICKS = 6         # at most this many files of one named folder besides its orienting files
ORIENTING_PICKS = 5      # at most this many orienting files of one named folder
RECENCY_WORDS = frozenset("latest newest recent recently last current newly".split())
HEADING = re.compile(r"^\s*(?:#{1,4}\s+(.+)|title\s*[:=]\s*(.+)|<title>(.*?)</title>|<h1[^>]*>(.*?)</h1>|(?:def|class|function|package|module)\s+(\w+))", re.I)
ENTITY = re.compile(r"\"([^\"\n]{3,40})\"|'([^'\n]{3,40})'|\b([\w-]*\d[\w-]*)\b|(?<=[a-z,;] )\b([A-Z][a-z]{2,}(?: [A-Z][a-z]{2,})*)\b")
REFERENCE = re.compile(r"[\w./-]+\.\w{1,5}")


def headings(head: str) -> str:
    found = []
    for line in head.splitlines()[:60]:
        match = HEADING.match(line)
        if match:
            found.append(next(g for g in match.groups() if g))
        if len(found) >= 4:
            break
    if not found:
        found = [next((l.strip() for l in head.splitlines() if l.strip()), "")]
    return " ".join(found)


def entities_of(text: str) -> Set[str]:
    out: Set[str] = set()
    for match in ENTITY.finditer(text):
        value = next(g for g in match.groups() if g).strip().lower()
        if len(value) >= 3 and not value.isdigit():
            out.add(value)
    return out


@implementation("folder-view", "evidence_ranked")
class EvidenceRanked:
    """Folders judged by evidence; files ranked by path, heading, opening, entity, link, trail and recency evidence."""
    REQUIRES = ()

    def __init__(self, bar: float = BAR, max_picks: int = MAX_PICKS):
        self.bar, self.max_picks = bar, max_picks

    def choose(self, goal: str, context: str, root: str, budget_chars: int = 100000, trail: Sequence[Mapping[str, Any]] = (),
               file_limit: int = 5000) -> FolderChoice:
        scanned = judgment.scan(root, file_limit, inspect=True, max_size=naming.FILE_LIMIT)
        out = FolderChoice(left_out=list(scanned.left_out), skipped=dict(scanned.skipped), scanned=len(scanned.files))
        text = goal + "\n" + context
        sizes = {rel: size for rel, size, _ in scanned.files}
        mtimes = {rel: mtime for rel, _, mtime in scanned.files}
        picks: List[Pick] = []
        flagged: Set[str] = set()
        named = naming.named_in(text, list(sizes))
        for rel in naming.named_paths(text, root):
            if rel in named or rel in flagged:
                continue
            verdict = judgment.path_verdict(root, rel)
            if verdict and verdict.risky:
                flagged.add(rel)
                picks.append(Pick(rel, "named in the goal, but " + verdict.reason, naming.size_of(root, rel), flagged=verdict.reason))
            else:
                named.append(rel)
                sizes.setdefault(rel, naming.size_of(root, rel))
        for left in scanned.left_out:        # a risky file at a level the scan listed (a .env beside the work) that the goal names
            if left.is_file and left.path not in flagged and naming.mentions(text, left.path):
                flagged.add(left.path)
                picks.append(Pick(left.path, "named in the goal, but " + left.reason, naming.size_of(root, left.path), flagged=left.reason))
        heads = scanned.heads
        dirs = named_folders.directories(list(sizes))
        for folder in named_folders.unreached(text, root, dirs):         # a folder the scan cap did not reach: scan it directly, as a named file is resolved
            inner = judgment.scan(os.path.join(root, folder), judgment.SNAPSHOT_FILES, inspect=True, max_size=naming.FILE_LIMIT)
            for rel, size, mtime in inner.files:
                sizes[folder + "/" + rel], mtimes[folder + "/" + rel] = size, mtime
                heads[folder + "/" + rel] = inner.heads.get(rel, "")
            for x in inner.left_out:
                out.left_out.append(LeftOut(folder + "/" + x.path, x.reason, x.kind, x.risky, x.is_file))
            dirs = named_folders.directories(list(sizes))
        used = 0
        for rel in named:
            size = min(sizes.get(rel, 0), budget_chars)
            picks.append(Pick(rel, "named in the goal or context", size, named=True))
            used += size
        taken = set(named)
        folders = named_folders.named(text, dirs)
        fill_in = min(budget_chars, used + FILL)
        for folder in folders:
            members = [r for r in dirs[folder] if r not in taken]
            order = named_folders.orienting(folder, members, mtimes, dirs)
            strong = [(r, w) for r, w, ok in order if ok][:ORIENTING_PICKS]
            weak = [(r, w) for r, w, ok in order if not ok]
            chosen = [(r, "an orienting file of the named folder " + folder + ": " + w) for r, w in strong]
            leftover = [r for r in members if r not in {c for c, _ in chosen}]
            topic_scores, topic_why = self.evidence(goal, context, leftover, heads, mtimes, named + [folder], root, trail, set(sizes))
            pointed = [r for r in sorted(leftover, key=lambda r: (-topic_scores.get(r, 0.0), sizes[r])) if topic_scores.get(r, 0.0) >= FOLDER_BAR][:FOLDER_PICKS]
            chosen += [(r, "in the named folder " + folder + ": " + (topic_why.get(r) or "likely")) for r in pointed]
            chosen += [(r, "in the named folder " + folder + ": " + w) for r, w in weak if r not in pointed][:1]
            for rel, why_text in chosen:
                size = min(sizes[rel], budget_chars)
                if used + size > fill_in or rel in taken:
                    continue
                picks.append(Pick(rel, why_text, size))
                taken.add(rel)
                used += size
        rest = [rel for rel in sizes if rel not in taken]
        scores, why = self.evidence(goal, context, rest, heads, mtimes, named + folders, root, trail, set(sizes))
        fits = used + sum(min(sizes[r], budget_chars) for r in rest) <= budget_chars
        if fits:
            ranked = sorted(rest, key=lambda r: (-scores.get(r, 0.0), sizes[r]))
            fill, limit = budget_chars, len(ranked)
        else:
            ranked = [r for r in sorted(rest, key=lambda r: (-scores[r], sizes[r])) if scores[r] >= self.bar]
            fill, limit = min(budget_chars, used + FILL), self.max_picks
        count = 0
        for rel in ranked:
            size = min(sizes[rel], budget_chars)
            if used + size > fill or count >= limit:
                continue
            picks.append(Pick(rel, why.get(rel) or ("the whole folder fits in the view" if fits else "likely"), size))
            used += size
            count += 1
        out.picks = picks
        return out

    def evidence(self, goal: str, context: str, rest: List[str], heads: Mapping[str, str], mtimes: Mapping[str, float], named: List[str],
                 root: str, trail: Sequence[Mapping[str, Any]], known: Set[str]) -> Tuple[Dict[str, float], Dict[str, str]]:
        """``({path: evidence}, {path: the evidence in words})`` for the files in ``rest``."""
        if not rest:
            return {}, {}
        topic, background = goal, context
        for rel in named:                      # the words of a path the goal gives name the file, they are not the topic
            topic = topic.replace(rel, " ").replace(rel.rsplit("/", 1)[-1], " ")
            background = background.replace(rel, " ").replace(rel.rsplit("/", 1)[-1], " ")
        weights: Counter = Counter()
        for word in tokens(background):
            weights[word] = CONTEXT_SHARE
        for word in tokens(topic):
            weights[word] = 1.0
        for word in IGNORED | set(tokens(" ".join(RECENCY_WORDS))) | {"most"}:      # asking for the latest says which, not what
            weights.pop(word, None)
        # Only a file that holds a probe of a goal word (the word's first letters, so a plural or a past tense still matches) is read into words: any file that
        # holds a word is such a candidate, so the document frequencies of the goal's words are exact and the other files cost one substring test each.
        probes = {w: w[:4] for w in weights}
        lows = {rel: (rel + "\n" + (heads.get(rel) or "")).lower() for rel in rest}
        candidates = [rel for rel in rest if any(p in lows[rel] for p in probes.values())]
        empty: Tuple[Set[str], Set[str], Set[str]] = (set(), set(), set())
        field_words = {rel: empty for rel in rest}
        for rel in candidates:
            field_words[rel] = (set(tokens(rel.replace("/", " "))), set(tokens(headings(heads.get(rel) or ""))), set(tokens(heads.get(rel) or "")))
        total = len(rest)
        df = [Counter(), Counter(), Counter()]        # per field: a word rare in paths says much even when every body holds it
        for fields in field_words.values():
            for counter, words in zip(df, fields):
                counter.update(words)
        names = ("path", "title", "body")
        for word in [w for w in weights if not any(counter.get(w) for counter in df)]:      # a word no file holds cannot tell the files apart
            del weights[word]
        idf = [{w: math.log((total + 1) / max(counter.get(w, 0), 1)) for w in weights} for counter in df]
        top = sum(weights.values()) * FIELD_WEIGHTS["title"] * math.log(total + 1)
        entities = entities_of(goal)
        links = self.linked(named, known, root)
        trailed = {str(t.get("path")): (TRAIL_WEIGHT + (0.2 if t.get("changed") else 0.0)) for t in trail if isinstance(t, Mapping)}
        scores: Dict[str, float] = {}
        why: Dict[str, str] = {}
        for rel in rest:
            fields = field_words[rel]
            raw, where = 0.0, []
            if fields is not empty:
                best = {w: max(FIELD_WEIGHTS[n] * idf[i][w] for i, n in enumerate(names) if w in fields[i]) for w in weights if any(w in f for f in fields)}
                raw = sum(weights[w] * v for w, v in best.items())
                where = [label for i, label in enumerate(("the path", "the headings", "the opening")) if any(w in fields[i] and idf[i][w] > 0 for w in weights)]
            score = raw / top if top > 0 else 0.0
            notes = []
            if where:
                notes.append("words of the goal in " + ", ".join(where))
            found = [e for e in entities if e in lows[rel]]
            if found:
                score += min(1.0, ENTITY_WEIGHT * len(found))
                notes.append("names " + ", ".join(sorted(found)[:3]))
            if rel in links:
                score += LINK_WEIGHT
                notes.append("linked from " + links[rel])
            if rel in trailed:
                score += trailed[rel]
                notes.append("earlier runs used it")
            scores[rel] = score
            why[rel] = "; ".join(notes)
        if RECENCY_WORDS & set(re.findall(r"[a-z]+", goal.lower())):
            self.latest(rest, scores, why, mtimes)
        return scores, why

    def latest(self, rest: List[str], scores: Dict[str, float], why: Dict[str, str], mtimes: Mapping[str, float]) -> None:
        """The goal asks for the latest: of a numbered series (names alike but for digits) only the newest stays a candidate."""
        families: Dict[str, List[str]] = {}
        for rel in rest:
            families.setdefault(re.sub(r"\d+", "#", rel), []).append(rel)
        for members in families.values():
            if len(members) < 3 or not any(scores[m] >= BAR for m in members):
                continue
            newest = max(members, key=lambda m: (mtimes.get(m, 0), m))
            for m in members:
                if m == newest:
                    scores[m] += RECENT_WEIGHT
                    why[m] = (why.get(m, "") + "; " if why.get(m) else "") + "the newest of its series"
                else:
                    scores[m] = min(scores[m], BAR / 2)

    def linked(self, named: List[str], known: Set[str], root: str) -> Dict[str, str]:
        """``{path: the named file that refers to it}``: by a path or a file name written in the named file, or a Python import."""
        found: Dict[str, str] = {}
        by_name: Dict[str, List[str]] = {}
        for rel in known:
            by_name.setdefault(rel.rsplit("/", 1)[-1], []).append(rel)
        for rel in named[:5]:
            try:
                with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as handle:
                    body = handle.read(40_000)
            except OSError:
                continue
            for ref in set(REFERENCE.findall(body)):
                ref = ref.strip("./")
                for target in ([ref] if ref in known else by_name.get(ref.rsplit("/", 1)[-1], [])):
                    if target != rel and target not in named:
                        found.setdefault(target, rel)
            if rel.endswith(".py"):
                for target in python_imports(rel, body, known):
                    if target not in named:
                        found.setdefault(target, rel)
        return found
