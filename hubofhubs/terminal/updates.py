"""Interim replies and the "Earlier updates (n)" fold.

A turn is a group of messages with one ``turn_id``: interims (work continues), at most one ask, and the final reply. The rule is the
Quest app's (``utils/replyUpdates.ts``): the LAST message of a group is open; every earlier one folds into one row, "Earlier
updates (n)", with a one-line preview of the latest folded update. A group of one is unchanged. A replayed message (same turn and
seq twice) shows once. Grouping reads stored fields only, never the words.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .blocks import Block, removed
from .strings import say

EARLIER_PREVIEW_CHARS = 90


@dataclass(frozen=True)
class TurnMessage:
    turn_id: str
    seq: int
    kind: str                      # "interim" | "ask" | "final"
    text: str = ""
    why_more: str = ""
    next: str = ""
    ask: Optional[Mapping[str, Any]] = None
    outcome: str = ""
    stop_reason: str = ""

    @property
    def key(self) -> str:
        return f"msg:{self.turn_id}:{self.seq}"


def interim_message(turn_id: str, seq: int, text: str, data: Optional[Mapping[str, Any]] = None) -> TurnMessage:
    """An interim event (``text`` and ``data``) as a message of the turn. ``data`` may be the older shape, with no why or next."""
    data = data or {}
    done = str(data.get("done") or "").strip()
    return TurnMessage(turn_id, seq, "interim", text=done or str(text or "").strip(),
                       why_more=str(data.get("why_more") or "").strip(), next=str(data.get("next") or "").strip())


def interim_parts(message: TurnMessage) -> Tuple[str, str]:
    """The two lines under an interim's text: the gap, and what happens next. Empty ones are dropped, and a next that restates the gap."""
    why, nxt = message.why_more.strip(), message.next.strip()
    if nxt and why and nxt.lower() == why.lower():
        nxt = ""
    return why, nxt


def earlier_preview(earlier: Sequence[TurnMessage]) -> str:
    """The first sentence of the latest folded update that has any text, flattened and cut at a word boundary."""
    for message in reversed(earlier):
        source = message.text.strip() or (message.ask or {}).get("question", "") or message.why_more
        flat = re.sub(r"```[\s\S]*?```", " ", str(source))
        flat = re.sub(r"[*_`#>]+", "", flat)
        flat = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", flat)
        flat = re.sub(r"\s+", " ", flat).strip()
        if not flat:
            continue
        m = re.match(r"^.*?[.!?](?=\s|$)", flat)
        sentence = m.group(0) if m else flat
        if len(sentence) <= EARLIER_PREVIEW_CHARS:
            return sentence
        cut = sentence[:EARLIER_PREVIEW_CHARS]
        at = cut.rfind(" ")
        return (cut[:at] if at > 40 else cut).rstrip() + "…"
    return ""


def group(messages: Sequence[TurnMessage]) -> Tuple[List[TurnMessage], Optional[TurnMessage]]:
    """``(earlier, latest)`` of one turn's messages: ordered by seq, a replayed seq kept once (the later copy)."""
    kept: Dict[int, TurnMessage] = {}
    for m in messages:
        kept[m.seq] = m
    ordered = [kept[s] for s in sorted(kept)]
    return (ordered[:-1], ordered[-1]) if ordered else ([], None)


def earlier_title(count: int, overrides=None) -> str:
    return say("replyUpdates.earlier.collapsed", overrides, count=count)


def interim_block(message: TurnMessage, overrides=None) -> Block:
    why, nxt = interim_parts(message)
    rows = tuple(r for r in (
        f"{say('replyUpdates.interim.whyLabel', overrides)}: {why}" if why else "",
        f"{say('replyUpdates.interim.nextLabel', overrides)}: {nxt}" if nxt else "") if r)
    return Block(kind="interim", title=say("replyUpdates.interim.label", overrides), text=message.text, rows=rows,
                 state="open", fold_key=message.key, style="plain")


def folded_row(turn_id: str, earlier: Sequence[TurnMessage], expanded: bool = False, overrides=None) -> Optional[Block]:
    """The one "Earlier updates (n)" row, closed with a preview or open with each folded update. None when nothing is folded."""
    if not earlier:
        return None
    key = f"updates:{turn_id}"
    title = earlier_title(len(earlier), overrides)
    if not expanded:
        return Block(kind="earlier_updates", title=title, text=earlier_preview(earlier), state="folded", fold_key=key, style="muted",
                     actions=(("expand_updates", "Show"),))
    rows: List[str] = []
    for m in earlier:
        rows.append(m.text or (m.ask or {}).get("question", "") or m.why_more)
        why, nxt = interim_parts(m)
        if why:
            rows.append(f"  {say('replyUpdates.interim.whyLabel', overrides)}: {why}")
        if nxt:
            rows.append(f"  {say('replyUpdates.interim.nextLabel', overrides)}: {nxt}")
    return Block(kind="earlier_updates", title=title, rows=tuple(r for r in rows if r), state="expanded", fold_key=key, style="muted",
                 actions=(("collapse_updates", "Hide"),))


def blocks_for(messages: Sequence[TurnMessage], latest_block, expanded: bool = False, overrides=None) -> List[Block]:
    """The blocks for a turn's messages while the newest is ``latest_block`` (a function message -> Block): the folded row, then it."""
    earlier, latest = group(messages)
    out: List[Block] = [removed(m.key) for m in earlier]
    row = folded_row(latest.turn_id, earlier, expanded, overrides) if latest else None
    if row:
        out.append(row)
    if latest:
        out.append(latest_block(latest))
    return out
