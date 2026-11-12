"""What the person and the harness are told about the context gathered: the brief added after the goal, and the one short line on screen."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from hubofhubs.the_intelligence.subconscious.focus_context.notes import Note

RULE = ("Background only: it is not part of the request and is never the answer. Answer exactly what was asked. Use a note only when it helps with that, and never list, "
        "summarize or mention notes the request did not ask about. When the request is about the person's own practice, work or interests (\"my ...\"), start from these notes "
        "and search files only for what they do not say. When you hand work to a helper, put the notes that bear on its task in the helper's description.")


@dataclass(frozen=True)
class FocusContext:
    """What one gathering found: the ``notes`` to show (best first), the ``brief`` text for the harness ("" when there are none) and the on-screen ``line`` ("" when none)."""
    focus: str
    notes: Sequence[Note] = ()
    brief: str = ""
    line: str = ""

    @property
    def ids(self) -> list:
        return [note.id for note in self.notes]


def line_of(count: int, focus: str) -> str:
    """The one line the person reads: ``Using 4 saved notes about garden``. Nothing when no note was used."""
    if count <= 0:
        return ""
    noun = "saved note" if count == 1 else "saved notes"
    return f"Using {count} {noun} about {focus}" if focus else f"Using {count} {noun}"


def brief_of(notes: Sequence[Note], focus: str) -> str:
    """The text added after the goal: what is already known (each note numbered with its title), then the rule for using it."""
    if not notes:
        return ""
    head = f"What is already known about {focus}, saved by the person:" if focus else "What is already known, saved by the person:"
    body = "\n\n".join(f"[{number}] {note.title}\n{note.text}".rstrip() for number, note in enumerate(notes, 1))
    return f"{head}\n\n{body}\n\n{RULE}"


def context_of(focus: str, notes: Sequence[Note]) -> FocusContext:
    notes = tuple(notes)
    return FocusContext(focus=focus, notes=notes, brief=brief_of(notes, focus), line=line_of(len(notes), focus))
