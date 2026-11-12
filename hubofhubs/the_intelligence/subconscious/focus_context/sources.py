"""Reading the sources of ``ContextSettings`` into notes. A source that cannot be read is a problem line, never a failed run (context only enriches)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_intelligence.subconscious.focus_context.notes import EXCERPT_CHARS, Note, note_of, notes_from_json
from hubofhubs.the_intelligence.subconscious.focus_context.settings import ContextSettings, Source

FILE_LIMIT = 3000
TEXT_SUFFIXES = (".md", ".txt")

Provider = Callable[[str], Iterable[Mapping[str, Any]]]


def cards_in(folder: str, focus: str) -> Tuple[List[Note], List[str]]:
    """Every ``*.json`` file of a folder of saved cards (one card, or a list of cards, per file)."""
    root = Path(folder)
    if not root.is_dir():
        return [], [f"the cards folder {folder} does not exist"]
    notes: List[Note] = []
    for number, path in enumerate(sorted(root.glob("*.json"))):
        if number >= FILE_LIMIT:
            break
        try:
            notes += notes_from_json(path.read_text(encoding="utf-8", errors="replace"), focus)
        except OSError:
            continue
    return notes, []


def folder_notes(folder: str, focus: str) -> Tuple[List[Note], List[str]]:
    """Each text file of a folder is one note: its first heading (or file name) is the title and its opening is the text."""
    root = Path(folder)
    if not root.is_dir():
        return [], [f"the folder {folder} does not exist"]
    notes: List[Note] = []
    for number, path in enumerate(sorted(p for p in root.rglob("*") if p.suffix.lower() in TEXT_SUFFIXES and p.is_file())):
        if number >= FILE_LIMIT:
            break
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read(EXCERPT_CHARS * 4)
        except OSError:
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0].lstrip("# ").strip() if lines else path.stem
        note = note_of({"id": str(path.relative_to(root)), "title": title or path.stem, "text": " ".join(lines[1:] if lines else ()),
                        "timestamp": ""}, focus)
        if note is not None:
            notes.append(note)
    return notes, []


def command_notes(source: Source, focus: str, environ: Optional[Mapping[str, str]] = None) -> Tuple[List[Note], List[str]]:
    """The notes a program prints as JSON; the program is told the focus in ``AHOHS_FOCUS`` and runs without a shell."""
    env = {**(environ or {}), "AHOHS_FOCUS": focus}
    try:
        done = subprocess.run(list(source.command), capture_output=True, text=True, timeout=source.timeout, env=env, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        return [], [f"the program {Path(source.command[0]).name} could not run: {type(error).__name__}"]
    if done.returncode != 0:
        return [], [f"the program {Path(source.command[0]).name} stopped with code {done.returncode}"]
    return list(notes_from_json(done.stdout, focus)), []


def load_notes(settings: ContextSettings, provider: Optional[Provider] = None, environ: Optional[Mapping[str, str]] = None) -> Tuple[Tuple[Note, ...], List[str]]:
    """All notes of the settings' sources (and of a consumer's ``provider(focus)``), each id once, with a plain line for every source that failed."""
    notes: List[Note] = []
    problems: List[str] = []
    for source in settings.sources:
        focus = source.focus or settings.focus
        if source.kind == "cards":
            found, bad = cards_in(source.path, focus)
        elif source.kind == "folder":
            found, bad = folder_notes(source.path, focus)
        else:
            found, bad = command_notes(source, focus, environ)
        notes += found
        problems += bad
    if provider is not None:
        try:
            raw = list(provider(settings.focus))
            notes += [n for n in (note_of(item, settings.focus, fallback_id=f"provided-{k}") for k, item in enumerate(raw, 1)) if n is not None]
        except Exception as error:  # noqa: BLE001 -- a consumer's provider that fails is said, never a failed run
            problems.append(f"the consumer's provider failed: {type(error).__name__}")
    seen: dict = {}
    for note in notes:
        seen.setdefault(note.id, note)
    return tuple(seen.values()), problems


__all__ = ["load_notes", "cards_in", "folder_notes", "command_notes", "Provider"]
