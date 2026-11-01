"""An ask: the run is blocked on a person and says so as a prompt block.

The block is drawn from the decision's fields, never from parsed text. For the person it is for: the question, one line on why only
they can answer, the options and a free-text answer, and "Not now", which folds it to one line and leaves the ask OPEN (nothing is
answered, declined or withdrawn). For anyone else: "Waiting on <name>" (the person who raised it also sees the question). Once
answered it settles to one quiet line. How an answer is sent (a decision resolve call) is the consumer's: ``AskAnswer`` is what
it gets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Tuple

from .blocks import Block
from .strings import say

ANSWER_MAX_CHARS = 2000


@dataclass(frozen=True)
class Ask:
    decision_id: str
    question: str
    why_only_you: str = ""
    done: str = ""
    options: Tuple[str, ...] = ()
    assigned_to: str = ""
    assigned_to_name: str = ""
    asker_id: str = ""


@dataclass(frozen=True)
class AskAnswer:
    """What to send for a typed answer: the resolution word and the person's own words."""
    resolution: str
    response_text: str


def ask_from_event(decision_id: str, data: Optional[Mapping[str, Any]], text: str = "") -> Optional[Ask]:
    """An ask from a decision event (``decision_id`` and its ``data``). None when there is no decision id or the data holds no
    ``question``: a decision that is only text (a parked approval, a clarifying question) is not an ask and keeps its own handling."""
    data = data or {}
    did = str(decision_id or data.get("decision_id") or "").strip()
    question = str(data.get("question") or "").strip()
    if not did or not question:
        return None
    options = tuple(str(o).strip() for o in (data.get("options") or []) if str(o).strip())
    return Ask(did, question, str(data.get("why_only_you") or "").strip(), str(data.get("done") or "").strip(), options,
               str(data.get("assigned_to") or "").strip(), str(data.get("assigned_to_name") or "").strip(),
               str(data.get("asker_user_id") or "").strip())


def is_for_viewer(ask: Ask, viewer_id: str = "") -> bool:
    """The ask is for the viewer when it is addressed to them, or to nobody else than the one who asked (the fallback)."""
    if not ask.assigned_to:
        return True
    who = viewer_id or ask.asker_id
    return not who or ask.assigned_to == who


def parse_answer(ask: Ask, typed: str) -> Optional[AskAnswer]:
    """A typed line as an answer. A number picks that option; anything else is free text (an option list never traps the person).
    Empty or longer than the limit: None."""
    line = (typed or "").strip()
    if not line or len(line) > ANSWER_MAX_CHARS:
        return None
    if ask.options and line.isdigit() and 1 <= int(line) <= len(ask.options):
        return AskAnswer("answered", ask.options[int(line) - 1])
    return AskAnswer("answered", line)


def ask_block(ask: Ask, viewer_id: str = "", folded: bool = False, overrides=None) -> Block:
    key = f"ask:{ask.decision_id}"
    if not is_for_viewer(ask, viewer_id):
        name = ask.assigned_to_name
        title = say("replyUpdates.ask.waitingOn", overrides, name=name) if name else say("replyUpdates.ask.waitingOnUnnamed", overrides)
        # The person who raised it sees the question too; nobody else's private question is shown.
        who = viewer_id or ask.asker_id
        shows = bool(who) and who == ask.asker_id
        return Block(kind="ask", title=title, text=ask.question if shows else "", state="waiting", fold_key=key, style="muted")
    if folded:
        return Block(kind="ask", title=say("replyUpdates.ask.foldedTitle", overrides), text=say("replyUpdates.ask.foldedBody", overrides),
                     state="folded", fold_key=key, style="muted", actions=(("answer_now", say("replyUpdates.ask.answerNow", overrides)),))
    rows: List[str] = []
    if ask.why_only_you:
        rows.append(ask.why_only_you)
    rows.extend(f"{i}. {o}" for i, o in enumerate(ask.options, 1))
    rows.append(say("replyUpdates.ask.silenceHold", overrides))
    actions = tuple((f"option:{i}", o) for i, o in enumerate(ask.options, 1)) + (
        ("send", say("replyUpdates.ask.send", overrides)), ("not_now", say("replyUpdates.ask.notNow", overrides)))
    return Block(kind="ask", title=say("replyUpdates.ask.needsYou", overrides), text=ask.question, rows=tuple(rows), state="open",
                 fold_key=key, style="emphasis", actions=actions)


def answered_block(ask: Ask, by_name: str = "", resumes: bool = False, overrides=None) -> Block:
    """The settled line: who answered, and whether the work is known to pick back up (only when it is)."""
    first = say("replyUpdates.ask.answeredBy", overrides, name=by_name) if by_name else say("replyUpdates.ask.answeredYou", overrides)
    second = say("replyUpdates.ask.resumes" if resumes else "replyUpdates.ask.saved", overrides)
    return Block(kind="ask", text=f"{first}. {second}", state="answered", fold_key=f"ask:{ask.decision_id}", style="muted")


def error_block(ask: Ask, overrides=None) -> Block:
    return Block(kind="line", text=say("replyUpdates.ask.error", overrides), style="warning", fold_key=f"ask-error:{ask.decision_id}")
