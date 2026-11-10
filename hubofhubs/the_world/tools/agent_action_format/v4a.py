"""The V4A patch format of OpenAI's ``apply_patch`` tool, applied inside a folder.

The Responses API returns one ``apply_patch_call`` item per file operation: ``{"type": "create_file" | "update_file" | "delete_file", "path", "diff"}``. A
``create_file`` diff is the new file (lines may carry a leading ``+``); an ``update_file`` diff holds hunks introduced by ``@@`` lines (optionally with a context
line after the marker), each made of context lines (leading space), removed lines (``-``) and added lines (``+``). A hunk is located by its context and removed
lines, exactly first and then ignoring trailing white space; a hunk that cannot be located fails the whole update with a message the model can act on. Paths stay
inside the folder. Standard library and the hub only.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Mapping, Tuple

from hubofhubs.the_world.tools.file_reading.read_files import inside


def hunks_of(diff: str) -> List[Tuple[List[str], List[str]]]:
    """``(old lines, new lines)`` of each hunk of an ``update_file`` diff."""
    hunks: List[Tuple[List[str], List[str]]] = []
    old: List[str] = []
    new: List[str] = []
    started = False
    for line in diff.splitlines():
        if line.startswith("@@"):
            if started and (old or new):
                hunks.append((old, new))
            old, new, started = [], [], True
            continue
        if line.startswith(("*** ", "---", "+++")) and not started:
            continue
        started = True
        if line.startswith("+"):
            new.append(line[1:])
        elif line.startswith("-"):
            old.append(line[1:])
        else:
            text = line[1:] if line.startswith(" ") else line
            old.append(text)
            new.append(text)
    if old or new:
        hunks.append((old, new))
    return hunks


def locate(lines: List[str], old: List[str], start: int) -> int:
    """The index at or after ``start`` where ``old`` occurs in ``lines`` (exact, then ignoring trailing white space), else -1; an empty ``old`` is the end of the file."""
    if not old:
        return len(lines)
    for compare in (lambda x: x, lambda x: x.rstrip(), lambda x: x.strip()):
        wanted = [compare(x) for x in old]
        for index in range(start, len(lines) - len(old) + 1):
            if [compare(x) for x in lines[index:index + len(old)]] == wanted:
                return index
    return -1


def apply_operation(root: str, operation: Mapping[str, object]) -> Tuple[bool, str]:
    """Apply one ``apply_patch_call`` operation in ``root``: ``(ok, message)``. Never raises."""
    kind, path, diff = str(operation.get("type") or ""), str(operation.get("path") or ""), str(operation.get("diff") or "")
    try:
        target = inside(Path(root), path)
        if kind == "delete_file":
            if not target.is_file():
                return False, f"Error: File not found at path '{path}'"
            target.unlink()
            return True, f"Deleted {path}"
        if kind == "create_file":
            body = [line[1:] if line.startswith("+") else line for line in diff.splitlines()]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(body) + ("\n" if body else ""), encoding="utf-8")
            return True, f"Created {path}"
        if kind != "update_file":
            return False, f"Error: unknown operation type {kind!r}"
        if not target.is_file():
            return False, f"Error: File not found at path '{path}'"
        text = target.read_text(encoding="utf-8")
        lines = text.split("\n")
        trailing = lines and lines[-1] == ""
        if trailing:
            lines = lines[:-1]
        cursor = 0
        for number, (old, new) in enumerate(hunks_of(diff), 1):
            at = locate(lines, old, cursor)
            if at < 0:
                return False, f"Error: hunk {number} of {path} does not match the file; its context or removed lines were not found. Read the file again and send a diff built from its current text."
            lines[at:at + len(old)] = new
            cursor = at + len(new)
        target.write_text("\n".join(lines) + ("\n" if trailing else ""), encoding="utf-8")
        return True, f"Updated {path}"
    except (OSError, ValueError) as error:
        return False, f"Error: {error}"
