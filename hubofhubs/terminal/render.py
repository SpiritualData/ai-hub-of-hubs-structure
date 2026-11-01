"""``render(event, state) -> blocks``: a run's progress events as blocks, with no UI library.

``TerminalState`` holds what one conversation needs between events (the turn's trace steps, messages and open ask). ``render`` reads
one event and returns the blocks that CHANGED, each with the ``fold_key`` of its place; a frontend replaces that place or appends.
``settle`` returns the blocks that close the turn (the folded updates, the one-line summary of the work, a stopped reason). Events
may be ``ProgressEvent`` objects or dicts. Only the event types below are handled; any other returns no blocks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from hubofhubs.ports.events import EVENT_DECISION, EVENT_INTERIM, EVENT_RESULT, EVENT_WORK_TRACE

from . import asks, stopped, trail, updates
from .blocks import Block, removed
from .strings import say

TRAIL_KEY = "trail"
#: How many rows a group shows before "Show all" (the Quest app's rule).
GROUP_ROWS = 5


@dataclass
class TerminalState:
    viewer_id: str = ""
    shared: bool = False                 # a thread with other people in it: record titles only when marked visible to all
    overrides: Any = None                # a profile's own words
    turn_id: str = ""
    steps: List[dict] = field(default_factory=list)
    messages: List[updates.TurnMessage] = field(default_factory=list)
    ask: Optional[asks.Ask] = None
    ask_folded: bool = False
    updates_expanded: bool = False
    trail_view: str = "closed"           # closed | open | all
    outcome: str = ""
    stop_reason: str = ""
    seq: int = 0

    def new_turn(self, turn_id: str) -> None:
        """Start a turn: its trace, messages, ask and outcome are fresh (the open ask of an earlier turn is kept)."""
        self.turn_id, self.steps, self.messages = turn_id, [], []
        self.updates_expanded, self.trail_view, self.outcome, self.stop_reason, self.seq = False, "closed", "", "", 0


def _field(event: Any, name: str, default: Any = None) -> Any:
    return event.get(name, default) if isinstance(event, dict) else getattr(event, name, default)


def render(event: Any, state: TerminalState) -> List[Block]:
    kind = _field(event, "type", "")
    data = _field(event, "data") or {}
    text = str(_field(event, "text") or "").strip()
    if kind == EVENT_WORK_TRACE:
        before = trail.live_text(state.steps, state.overrides)
        state.steps = trail.apply_event(state.steps, data)
        line = trail.live_text(state.steps, state.overrides)
        if line == before:
            return []
        return [Block(kind="trail_live", text=line, state="live", fold_key=TRAIL_KEY, style="muted")] if line else [
            removed(TRAIL_KEY)]
    if kind == EVENT_INTERIM:
        state.seq += 1
        message = updates.interim_message(state.turn_id, state.seq, text, data if isinstance(data, dict) else {})
        state.messages.append(message)
        return updates.blocks_for(state.messages, lambda m: updates.interim_block(m, state.overrides), state.updates_expanded, state.overrides)
    if kind == EVENT_DECISION:
        ask = asks.ask_from_event(_field(event, "decision_id", ""), data if isinstance(data, dict) else {}, text)
        if ask is None:
            return []
        state.ask, state.ask_folded = ask, False
        return [asks.ask_block(ask, state.viewer_id, False, state.overrides)]
    if kind == EVENT_RESULT and isinstance(data, dict):
        state.outcome = str(data.get("outcome") or "")
        state.stop_reason = str(data.get("stop_reason") or "")
    return []


def settle(state: TerminalState, can_continue: bool = True) -> List[Block]:
    """The blocks that close a turn, in order: every interim folded into "Earlier updates (n)" (the final reply is the open one),
    then the work summary, then a stopped reason with Continue. A turn that ended on an ask folds its interims the same way: the
    ask is the open message."""
    out: List[Block] = []
    interims = [m for m in state.messages if m.kind == "interim"]
    if interims:
        out.extend(removed(m.key) for m in interims)
        row = updates.folded_row(state.turn_id, interims, state.updates_expanded, state.overrides)
        if row:
            out.append(row)
    out.extend(trail_blocks(state))
    stop = stopped.stopped_block(state.outcome, state.stop_reason, state.overrides, can_continue)
    if stop:
        out.append(stop)
    return out


def trail_blocks(state: TerminalState) -> List[Block]:
    """The settled summary line, or with ``trail_view`` open the groups behind it. Nothing when the turn did no work worth a line."""
    steps = trail.redact_for_shared(state.steps) if state.shared else state.steps
    if not trail.has_visible_work(steps, state.shared):
        return [removed(TRAIL_KEY)]
    text = trail.summary_text(steps, state.shared, state.overrides)
    detail = trail.has_expandable_detail(steps, state.shared)
    groups = trail.expanded_groups(steps, state.shared, state.overrides) if state.trail_view != "closed" else []
    if state.trail_view == "closed" or not groups:
        actions = (("expand_trail", "Show details"),) if detail else ()
        return [Block(kind="trail_summary", text=text, state="settled", fold_key=TRAIL_KEY, style="muted", actions=actions)]
    rows: List[str] = []
    more = False
    for g in groups:
        shown = g["rows"] if state.trail_view == "all" else g["rows"][:GROUP_ROWS]
        more = more or len(shown) < len(g["rows"])
        if len(groups) > 1:
            rows.append(g["title"])
        rows.extend(f"  {r}" for r in shown)
        if len(shown) < len(g["rows"]):
            rows.append(f"  {say('workTrace.showAll', None, count=len(g['rows']))}")
        rows.extend(f"  {n}" for n in g["notes"])
    actions = (("show_all_trail", "Show all"),) if more else ()
    return [Block(kind="trail_summary", text=text, rows=tuple(rows), state="expanded", fold_key=TRAIL_KEY, style="muted",
                  actions=actions + (("collapse_trail", "Hide details"),))]


def toggle_trail(state: TerminalState) -> List[Block]:
    """Closed, then open (five rows a group), then all rows when some were left out, then closed."""
    if state.trail_view == "closed":
        state.trail_view = "open"
    elif state.trail_view == "open" and _has_more_rows(state):
        state.trail_view = "all"
    else:
        state.trail_view = "closed"
    return trail_blocks(state)


def _has_more_rows(state: TerminalState) -> bool:
    steps = trail.redact_for_shared(state.steps) if state.shared else state.steps
    return any(len(g["rows"]) > GROUP_ROWS for g in trail.expanded_groups(steps, state.shared, state.overrides))


def toggle_updates(state: TerminalState) -> List[Block]:
    state.updates_expanded = not state.updates_expanded
    interims = [m for m in state.messages if m.kind == "interim"]
    row = updates.folded_row(state.turn_id, interims, state.updates_expanded, state.overrides)
    return [row] if row else []


def fold_ask(state: TerminalState) -> List[Block]:
    """"Not now": the card folds to one line; the ask stays open (nothing is answered)."""
    if state.ask is None:
        return []
    state.ask_folded = True
    return [asks.ask_block(state.ask, state.viewer_id, True, state.overrides)]


def unfold_ask(state: TerminalState) -> List[Block]:
    if state.ask is None:
        return []
    state.ask_folded = False
    return [asks.ask_block(state.ask, state.viewer_id, False, state.overrides)]


def answer_ask(state: TerminalState, typed: str) -> Optional[asks.AskAnswer]:
    """The answer a typed line gives to the open ask, or None when nothing is asked of this viewer or the line is unusable."""
    ask = state.ask
    if ask is None or state.ask_folded or not asks.is_for_viewer(ask, state.viewer_id):
        return None
    return asks.parse_answer(ask, typed)


def close_ask(state: TerminalState, by_name: str = "", resumes: bool = False) -> List[Block]:
    """The ask was answered: it settles to one line and is no longer open."""
    ask, state.ask, state.ask_folded = state.ask, None, False
    return [asks.answered_block(ask, by_name, resumes, state.overrides)] if ask else []


def live_line(state: TerminalState) -> Optional[str]:
    return trail.live_text(state.steps, state.overrides)
