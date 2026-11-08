"""Holds a response's figures to the evidence: a sentence that states a figure the evidence does not hold is a finding, and ``repair`` takes it out.

Rule: a figure in a reply (a count, a rate, a day of the month) must come from the evidence: what the turn read, the context it was handed, or the person's own message. A figure
from nowhere (an old count recalled from memory, a target that no read shows, a date moved to another record) is how a status answer goes wrong, and a prompt line asking the model not to
leaks. The code reads digits only, never meaning: a sentence or bullet with a figure that no read holds is dropped; the rest of the reply stays. A reply that would be left empty is kept
whole (nothing is better than a blank), and a drafted deliverable (copy the person asked to have written) is not touched, since its numbers are the copy's own.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple

from esoi import implementation

FIGURE = re.compile(r"\d+(?:[.,]\d+)?")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9*\"'(\[])")
LIST_NUMBER = re.compile(r"^\s*(?:[-*•]\s*)?\d+[.)]\s+")
READ_ITEM_CHARS = 2500
CONTEXT_CHARS = 5000


def evidence_of(gathered: Iterable[Any], context_view: str, user_message: str) -> str:
    """What the turn read, as one text: each gathered result (its first ``READ_ITEM_CHARS`` characters), the start of the context it was handed, and the person's message."""
    parts: List[str] = [str(user_message or ""), str(context_view or "")[:CONTEXT_CHARS]]
    for item in gathered or []:
        if isinstance(item, Mapping) and not item.get("planner_only"):
            parts.append(str(item.get("tool_text") or item.get("text") or "")[:READ_ITEM_CHARS])
    return "\n".join(parts)


def figures_of(text: str) -> List[str]:
    return FIGURE.findall(LIST_NUMBER.sub("", text or ""))


def figure_value(figure: str) -> str:
    """A figure by value: leading zeros and a thousands comma aside, so "06" (in "2026-11-06") holds "6" (in "6 November") and "1,000" holds "1000"."""
    plain = figure.replace(",", "") if re.fullmatch(r"\d{1,3}(?:,\d{3})+", figure) else figure
    whole, dot, rest = plain.partition(".")
    return (whole.lstrip("0") or "0") + (dot + rest if dot else "")


def cut_unsupported(text: str, evidence: str) -> Tuple[str, List[str]]:
    """``(the reply without its unsupported sentences, the figures that were unsupported)``, even when nothing is left. Sentences are cut at line ends and sentence ends; a figure
    is supported when the same number occurs in the evidence as a whole number."""
    held = {figure_value(f) for f in FIGURE.findall(evidence or "")} | {figure_value(f) for f in re.findall(r"\d+", evidence or "")}
    kept: List[str] = []
    removed: List[str] = []
    for raw_line in str(text or "").split("\n"):
        numbered = LIST_NUMBER.match(raw_line)
        prefix, line = (numbered.group(0), raw_line[numbered.end():]) if numbered else ("", raw_line)         # "1. " opens a list item; it is not the end of a sentence
        pieces = SENTENCE_END.split(line) if line.strip() else [line]
        survivors = []
        for piece in pieces:
            bad = [f for f in figures_of(piece) if figure_value(f) not in held]
            if bad:
                removed.extend(bad)
            else:
                survivors.append(piece)
        if survivors or not line.strip():
            kept.append(prefix + " ".join(survivors) if survivors else raw_line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip(), removed


def strip_unsupported(text: str, evidence: str) -> Tuple[str, List[str]]:
    """``(the reply without its unsupported sentences, the figures that were unsupported)``; a reply that would be left empty is kept whole, with no figures reported."""
    result, removed = cut_unsupported(text, evidence)
    return (result, removed) if result else (str(text or ""), [])


@implementation("response-quality", "grounded_figures")
class GroundedFigures:
    """A response holds when every figure in it occurs in the evidence text; ``repair`` drops each sentence that states one that does not."""
    REQUIRES = ()     # pure functions

    def judge(self, response: str, evidence: str = "", profile: Optional[Any] = None) -> Sequence[str]:
        """One finding per figure the evidence does not hold, unless the profile lists no such criterion."""
        if profile is not None and getattr(profile, "criterion", None) and profile.criterion("faithfulness to evidence") is None:
            return []
        return self.critique(response, evidence)

    def critique(self, answer: str, evidence: str = "") -> Sequence[str]:
        return [f"figure not in the evidence: {figure}" for figure in dict.fromkeys(cut_unsupported(answer, evidence)[1])]

    def repair(self, response: str, evidence: str = "") -> str:
        return strip_unsupported(response, evidence)[0]
