"""Two sections of the hub's frame that a consumer's own material fills, built in code with no model call: the SKILLS the consumer keeps, and the KNOWN context.

Role: a session on the model's own tool loop starts from the folder alone. The consumer's skills (runbooks it wrote for kinds of work) never reached it, and neither did
what is already known: the consumer's recalled context and the earlier investigations of the solutions in scope. ``skills_section`` lists each skill in one line with the path of
its file (the session reads the file when the work is one it covers); ``known_section`` is bounded in characters and ordered, so the same inputs are the same bytes (the
provider's prompt cache keys on the start of the prompt). Standard library, and the hub's investigation store read lazily.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

SKILL_FILE = "SKILL.md"
SKILL_LINE_CHARS = 220
SKILLS_CHARS = 6000
KNOWN_CHARS = 6000
INVESTIGATION_CHARS = 320
SKILLS_RULE = "Read a skill's file before you do work it covers."
INVESTIGATION_RULE = "An earlier investigation listed here is not redone unless its date is stale."


def frontmatter(text: str) -> Dict[str, str]:
    """The ``key: value`` pairs of a file's leading ``---`` block; a value that continues on indented lines (or after ``>`` or ``|``) is joined into one line."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: Dict[str, str] = {}
    key = ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1] in (" ", "\t") and key:
            out[key] = (out[key] + " " + line.strip()).strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            out[key] = "" if value in (">", ">-", "|", "|-") else value.strip("\"'")
    return out


def clipped(text: str, chars: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= chars else text[:max(chars - 3, 0)].rstrip() + "..."


def skills_section(skills_dir: Union[None, str, Sequence[str]], chars: int = SKILLS_CHARS) -> str:
    """The SKILLS section for the folders of skills (one folder per skill with a ``SKILL.md``): one line per skill, ``name: description`` and the path of its file, sorted by name
    and clipped, then the rule. ``""`` when there are no skills. A folder or file that cannot be read is skipped."""
    folders = [skills_dir] if isinstance(skills_dir, (str, os.PathLike)) else list(skills_dir or ())
    found: Dict[str, str] = {}
    for folder in folders:
        try:
            entries = sorted(os.scandir(folder), key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path) / SKILL_FILE
            try:
                meta = frontmatter(path.read_text(encoding="utf-8", errors="replace")[:4000]) if entry.is_dir() and path.is_file() else None
            except OSError:
                meta = None
            if meta is None:
                continue
            name = meta.get("name") or entry.name
            found.setdefault(name, f"- {clipped(name + ': ' + meta.get('description', ''), SKILL_LINE_CHARS)} ({path})")
    if not found:
        return ""
    lines: List[str] = []
    used = 0
    for name in sorted(found):
        if used + len(found[name]) + 1 > chars:
            lines.append(f"... {len(found) - len(lines)} more skills not listed; list the skills folder to see them")
            break
        lines.append(found[name])
        used += len(found[name]) + 1
    return "SKILLS (the consumer's own; " + SKILLS_RULE + "):\n" + "\n".join(lines)


def investigation_line(row: Dict[str, Any]) -> str:
    """One line for a stored investigation: its question, its finding (what it found known, else what it decided) and its date, marked stale when past its revisit date."""
    finding = row.get("synthesis_known") or row.get("decisions") or row.get("decision") or ""
    date = row.get("done_on") or "undated"
    stale = ", stale" if str(row.get("fresh") or "") == "no" else ""
    return clipped(f"- {row.get('question', '')} | finding: {finding} | {date}{stale}", INVESTIGATION_CHARS)


def known_section(goal: str, *, recall: Optional[Callable[[str], str]] = None, solutions: Sequence[str] = (),
                  investigations: Optional[Callable[[str], Sequence[Dict[str, Any]]]] = None, chars: int = KNOWN_CHARS) -> str:
    """The KNOWN section, at most about ``chars`` characters: first the text ``recall(goal)`` returns (the consumer's cards or memory; at most
    three fifths of the room), then one line for each earlier investigation of the ``solutions`` in scope and the solutions above them (newest first, none twice), then the rule.
    ``investigations(solution_id)`` defaults to the hub's investigation store. A recall or a store that fails leaves its part out. ``""`` when there is nothing known."""
    room = int(chars)
    parts: List[str] = []
    try:
        text = str(recall(goal) or "").strip() if recall is not None else ""
    except Exception:  # noqa: BLE001 -- a recall that fails leaves its part out
        text = ""
    if text:
        text = text[:int(room * 0.6)].rstrip()
        parts.append("From the consumer's recalled context:\n" + text)
        room -= len(text)
    if investigations is None:
        from hubofhubs.the_world.learning.investigation_store import investigations_for
        investigations = lambda sid: investigations_for(sid, include_ancestors=True)    # noqa: E731
    rows: Dict[str, Dict[str, Any]] = {}
    for sid in sorted(set(solutions)):
        try:
            for row in investigations(sid) or ():
                rows.setdefault(str(row.get("investigation_id") or row.get("question")), dict(row))
        except Exception:  # noqa: BLE001
            continue
    lines: List[str] = []
    for row in sorted(rows.values(), key=lambda r: (str(r.get("done_on") or ""), str(r.get("investigation_id") or "")), reverse=True):
        line = investigation_line(row)
        if sum(len(x) + 1 for x in lines) + len(line) > max(room, 0):
            break
        lines.append(line)
    if lines:
        parts.append("Earlier investigations (" + INVESTIGATION_RULE + "):\n" + "\n".join(lines))
    return "KNOWN CONTEXT (already known; do not look it up again):\n" + "\n\n".join(parts) if parts else ""
