"""Small text helpers for status lines and briefs: cut to a length on a sensible boundary."""
from __future__ import annotations


def ellipsize(text: str, limit: int) -> str:
    """``text`` on one line, cut to ``limit`` characters with a trailing ellipsis when it is longer.

    The cut falls on a word boundary when one is near the end, so a title or a goal is not chopped
    mid-word, and the punctuation the cut leaves behind (a comma, a colon) goes with the cut-off words.
    """
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[: max(limit - 1, 1)]
    after = text[len(cut)]
    if not (after.isspace() or after in ",;:.!?)"):   # the cut is inside a word: back up to the word before
        space = cut.rfind(" ")
        if space >= limit * 0.6:
            cut = cut[:space]
    return cut.rstrip(" ,;:-–") + "…"


def sentence(text: str) -> str:
    """``text`` as a status sentence: ended with a full stop unless it already ends in one, in an ellipsis or in
    other closing punctuation."""
    text = text.rstrip()
    return text if not text or text.endswith((".", "…", "!", "?")) else text + "."


def clip_head_and_tail(text: str, limit: int) -> str:
    """``text`` cut to about ``limit`` chars keeping its START and its END. A queued task's brief
    opens with the standing request and ENDS with what the person just said; a head-only cut
    judged the brief on everything except the newest words."""
    if len(text) <= limit:
        return text
    head = limit * 2 // 5
    tail = limit - head
    return text[:head].rstrip() + "\n[...]\n" + text[-tail:].lstrip()
