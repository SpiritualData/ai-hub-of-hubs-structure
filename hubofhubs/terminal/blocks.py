"""The one value every terminal frontend draws: a ``Block``.

A block is plain data (no UI library, no styling objects). ``kind`` says what it is, ``style`` is a semantic name a frontend maps to
its own colours (``plain``, ``muted``, ``emphasis``, ``warning``), ``rows`` are the lines under ``text``, ``actions`` are the things
the person can do with it as ``(action id, label)`` pairs (the frontend binds keys to the ids), and ``fold_key`` names the place a
block lives: a later block with the same key REPLACES the earlier one in place, and ``state == "removed"`` takes the place away.
Text a renderer writes never holds an em dash (``clean``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

#: What a block can be. A frontend may draw an unknown kind as a plain paragraph.
KINDS = ("line", "trail_live", "trail_summary", "trail_group", "interim", "earlier_updates", "ask", "stopped")
STYLES = ("plain", "muted", "emphasis", "warning")


def clean(text: Any) -> str:
    """Code-written text for a screen: no em dash (a comma stands in), no stray newline at the ends."""
    return str(text or "").replace(" \u2014 ", ", ").replace("\u2014", ", ").strip("\n")


@dataclass(frozen=True)
class Block:
    kind: str = "line"
    text: str = ""
    rows: Tuple[str, ...] = ()
    #: A kind's own states, for example ``live``, ``settled``, ``open``, ``folded``, ``expanded``, ``waiting``, ``removed``.
    state: str = ""
    #: The place this block lives. Same key, later block: replace in place. Empty: just append.
    fold_key: str = ""
    title: str = ""
    style: str = "plain"
    actions: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", clean(self.text))
        object.__setattr__(self, "title", clean(self.title))
        object.__setattr__(self, "rows", tuple(clean(r) for r in self.rows))
        object.__setattr__(self, "actions", tuple((str(a), clean(label)) for a, label in self.actions))

    @property
    def removed(self) -> bool:
        return self.state == "removed"


def removed(fold_key: str) -> Block:
    """Take the place ``fold_key`` away (an earlier message folded into a row)."""
    return Block(kind="line", state="removed", fold_key=fold_key)


def to_text(blocks) -> str:
    """The blocks as plain text, the layer every frontend can fall back to (a removed block writes nothing)."""
    out = []
    for b in blocks:
        if b.removed:
            continue
        head = b.title if b.title and not b.text else (f"{b.title}: {b.text}" if b.title else b.text)
        if head:
            out.append(head)
        out.extend(f"  {r}" for r in b.rows)
        if b.actions:
            out.append("  [" + "] [".join(label for _, label in b.actions) + "]")
    return "\n".join(out)
